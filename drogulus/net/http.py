# -*- coding: utf-8 -*-
"""
Contains the classes used to implement HTTP connectivity. These classes
handle the network communication "down the wire" in a way that is opaque to
the local node (from its point of view, messages come in and messages go out).
"""
from ..dht.messages import to_dict, from_dict
from .connector import Connector
import aiohttp
import aiohttp.server
import logging
import asyncio
import json
import traceback
import re
import time


log = logging.getLogger(__name__)


class HttpConnector(Connector):
    """
    A connector child class that brokers between the HTTP network-y end
    of things and the local node within the DHT network.
    """

    def __init__(self, event_loop, clean_interval=None):
        super().__init__(event_loop)
        self.lookups = {}
        if not clean_interval:
            clean_interval = 60 * 5  # five minutes.
        event_loop.call_later(clean_interval, self._sweep_and_clean_cache,
                              event_loop, clean_interval)

    def _sweep_and_clean_cache(self, event_loop, clean_interval):
        """
        Removes items from the lookups cache that have not been requested
        within the past 'clean_interval' seconds. Once cleaned will reschedule
        itself to be run in clean_interval seconds time.
        """
        now = time.time()
        stale_if_not_called_after = now - clean_interval
        stale_items = []
        for k, v in self.lookups.items():
            if v['last_access'] < stale_if_not_called_after:
                stale_items.append(k)
        for key in stale_items:
            del(self.lookups[key])
        event_loop.call_later(clean_interval, self._sweep_and_clean_cache,
                              event_loop, clean_interval)

    def send(self, contact, message, sender=None):
        """
        Sends the message to the referenced contact. The sender argument isn't
        required for the HTTP implementation.
        """
        payload = to_dict(message)
        headers = {'content-type': 'application/json'}
        return asyncio.Task(aiohttp.request('post',
                                            contact.uri,
                                            data=json.dumps(payload),
                                            headers=headers))

    def receive(self, raw, sender, local_node):
        """
        Called when a message is received from a remote node on the network.
        The local_node handles the incoming request and returns an appropriate
        response message (if required).
        """
        try:
            message_dict = json.loads(raw.decode('utf-8'))
            message = from_dict(message_dict)
            return local_node.message_received(message, 'http', sender,
                                               message.reply_port)
        except Exception as ex:
            # There's not a lot that can be usefully done at this stage except
            # to log the problem in a way that may aid further investigation.
            log.error('Problem message received from {}'.format(sender))
            log.exception(ex)
            log.error(traceback.format_exc())
            log.error(raw)
            # Will cause generic 500 HTTP error response.
            raise ex

    def get(self, key, local_node, forced=False):
        """
        An HttpConnector only utility method for conveniently getting values
        from the drogulus as GET requests.

        Given the key (a sha512 hexdigest) this method will check if there is
        already an existing lookup for the key. If found it returns the status
        of the lookup (a future) and, if appropriate, the associated value.

        If the 'forced' flag is set any cached values are ignored and
        refreshed with a new lookup value.

        If no such lookup associated with the referenced key exists then a
        new lookup is created and a "pending" result is returned on the
        assumption that the user will poll later.

        The lookup itself and an associated 'last_access' value (containing
        a timestamp indicating when the value was last requested) are stored
        in the cache. The 'last_access' value is used to check if an item
        should be removed from the cache during a sweep and clean scheduled
        every X seconds interval.
        """

        lookup = None
        if key in self.lookups and not forced:
            lookup = self.lookups[key]['lookup']
            self.lookups[key]['last_access'] = time.time()
        else:
            lookup = local_node.retrieve(key)
            self.lookups[key] = {
                'last_access': time.time(),
                'lookup': lookup
            }
        result = {'key': key}
        result['status'] = lookup._state.lower()
        if lookup.done():
            try:
                result['value'] = lookup.result()
            except:
                result['error'] = True
        return result


class HttpRequestHandler(aiohttp.server.ServerHttpProtocol):
    """
    A class that defines the behaviour of handling HTTP requests.
    """

    def __init__(self, connector, node, **kwargs):
        """
        Ensure there's a reference to the local node.
        """
        super().__init__(**kwargs)
        self.connector = connector
        self.node = node

    @asyncio.coroutine
    def handle_request(self, message, payload):
        """
        Handles a request.
        """
        response_code = 405  # Method Not Allowed
        headers = {}
        headers['Content-Type'] = 'application/json'
        data = {}
        if message.method == 'POST':
            try:
                raw_data = yield from payload.read()
                peer = self.transport.get_extra_info('peername')[0]
                log.info(peer)
                log.info(raw_data)
                result = self.connector.receive(raw_data, peer, self.node)
                if result:
                    data = to_dict(result)
                response_code = 200  # OK
            except Exception as ex:
                # We log any errors in the connector / node instances so,
                # if there's is an exception then there's something wrong
                # with the connector (so return an error message to the
                # client).
                log.error(ex)
                response_code = 500  # Internal Server Error
        elif message.method == 'GET':
            try:
                # Get the sha512 key from the path.
                key = message.path[1:].lower()
                log.info(key)
                # Check the key is a valid sha512 value.
                if len(key) == 128 and re.match('^[a-z0-9]+$', key):
                    # Expect a single cache-control header with the value
                    # no-cache in order to force an update.
                    forced = False
                    cache_control = [v.lower().strip() for k, v
                                     in message.headers.items()
                                     if k.lower() == 'cache-control']
                    if len(cache_control) == 1:
                        forced = cache_control[0] == 'no-cache'
                    data = self.connector.get(key, self.node, forced)
                    response_code = 200  # OK
                else:
                    # wrong length or bad value
                    response_code = 400  # Bad Request
            except Exception as ex:
                log.error(ex)
                response_code = 500  # Internal Server Error
        raw_output = json.dumps(data).encode('utf-8')
        headers['Content-Length'] = str(len(raw_output))
        response = aiohttp.Response(self.writer, response_code,
                                    http_version=message.version)
        for k, v in headers.items():
            response.add_header(k, v)
        response.send_headers()
        response.write(raw_output)
        yield from response.write_eof()
