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


log = logging.getLogger(__name__)


class HttpConnector(Connector):
    """
    A connector child class that brokers between the HTTP network-y end
    of things and the local node within the DHT network.
    """

    def __init__(self, event_loop):
        super().__init__(event_loop)
        self.lookups = {}
        # TODO: Set call_later to sweep and clean lookups cache.

    def send(self, contact, message):
        """
        Sends the message to the referenced contact.
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

    def get(self, key, local_node):
        """
        An HttpConnector only utility method for conveniently getting values
        from the drogulus as GET requests.

        Given the key (a sha512 hexdigest) this method will check if there is
        already an existing lookup for the key. If found it returns the status
        of the lookup (a future) and, if appropriate, the associated value.

        If no such lookup associated with the referenced key exists then a
        new lookup is created and a "pending" result if returned on the
        assumption that the user will poll later.
        """

        # TODO: Schedule sweep and clean of cache.
        # TODO: Force update.
        lookup = None
        if key in self.lookups:
            lookup = self.lookups[key]
        else:
            lookup = local_node.retrieve(key)
            self.lookups[key] = lookup
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
            except:
                # We log any errors in the connector / node instances so,
                # nothing to do here but return an error message to the
                # client.
                response_code = 500  # Internal Server Error
        elif message.method == 'GET':
            try:
                # Get the sha512 key from the path.
                key = message.path[1:].lower()
                log.info(key)
                # Check the key is a valid sha512 value.
                if len(key) == 128 and re.match('^[a-z0-9]+$', key):
                    data = self.connector.get(key, self.node)
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
