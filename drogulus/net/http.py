# -*- coding: utf-8 -*-
"""
Contains the classes used to implement HTTP connectivity. These classes
handle the network communication "down the wire" in a way that is opaque to
the local node (from its point of view, messages come in and messages go out).
"""
from ..dht.messages import to_dict, from_dict
from ..dht.crypto import verify_item
from ..dht.constants import DUPLICATION_COUNT
from .connector import Connector
from aiohttp import web
import aiohttp
import aiohttp.server
import logging
import asyncio
import json
import traceback
import time
import jinja2
import os


DEFAULT_CLEAN_INTERVAL = 60 * 15  # 15 minutes


log = logging.getLogger(__name__)


class HttpConnector(Connector):
    """
    A connector child class that brokers between the HTTP network-y end
    of things and the local node within the DHT network.
    """

    def __init__(self, event_loop, clean_interval=DEFAULT_CLEAN_INTERVAL):
        super().__init__(event_loop)
        self.lookups = {}
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

    @asyncio.coroutine
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
        An ApplicationHandler only utility method for conveniently getting
        values from the drogulus as GET requests.

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
                result['result'] = lookup.result()
            except:
                result['error'] = True
        return result

    def set(self, local_node, key, value, timestamp, expires, created_with,
            public_key, name, signature):
        """
        Given the passed in arguments will validate them and then set them
        within the DHT.

        The result is a dictionary indication of the set action's status (to be
        ultimately JSONified).
        """
        item = {
            'key': key,
            'value': value,
            'timestamp': timestamp,
            'expires': expires,
            'created_with': created_with,
            'public_key': public_key,
            'name': name,
            'signature': signature,
        }
        if verify_item(item):
            setter = local_node.replicate(DUPLICATION_COUNT, item['key'],
                                          item['value'], item['timestamp'],
                                          item['expires'],
                                          item['created_with'],
                                          item['public_key'], item['name'],
                                          item['signature'])
            result = item.copy()
            result['status'] = setter._state.lower()
            return result
        else:
            error = 'Unable to validate item.'
            log.error(error)
            log.error(item)
            raise ValueError(error)


class ApplicationHandler:
    """
    A class that defines the methods to handle specific HTTP ACTION/PATH
    combinations.
    """

    def __init__(self, event_loop, connector, local_node):
        """
        The event loop, connector and local_node arguments are all
        stored as instance attributes to be referenced by the coroutine
        methods.
        """
        self.event_loop = event_loop
        self.connector = connector
        self.local_node = local_node
        self.resource_path = os.path.join(os.path.dirname(__file__),
                                          'web_resources')
        loader = jinja2.FileSystemLoader(self.resource_path)
        self.template_env = jinja2.Environment(loader=loader)

    @asyncio.coroutine
    def dht_traffic(self, request):
        """
        Handle all DHT related traffic (JSON).
        """
        data = None
        try:
            raw_data = yield from request.read()
            peer = request.transport.get_extra_info('peername')[0]
            log.info(peer)
            log.info(raw_data)
            result = yield from self.connector.receive(raw_data, peer,
                                                       self.local_node)
            data = to_dict(result)
        except Exception as ex:
            # We log any errors in the connector / node instances,
            # so return an appropriate error to the caller.
            log.error(ex)
            raise web.HTTPInternalServerError
        raw_output = json.dumps(data).encode('utf-8')
        return web.Response(body=raw_output, status=200,
                            content_type='application/json')

    @asyncio.coroutine
    def home(self, request):
        """
        Return the HTML for the local_node's home page.
        """
        template = self.template_env.get_template('index.html')
        result = template.render(node_id=self.local_node.network_id)
        return web.Response(body=result.encode('utf-8'), status=200)

    @asyncio.coroutine
    def set_value(self, request):
        """
        POST to /<key> - sets a value to the referenced sha512 key.
        """
        # Get the sha512 key from the path.
        key = request.path[1:].lower()
        log.info('HTTP POST value to {}'.format(key))
        # Extract the JSON
        raw_data = yield from request.read()
        try:
            data = json.loads(raw_data.decode('utf-8'))
            log.info(data)
            expected_fields = ['key', 'value', 'timestamp', 'expires',
                               'created_with', 'public_key', 'name',
                               'signature']
            # Validate the syntax of the incoming data.
            if len(data) == len(expected_fields):
                for field in data:
                    if field not in expected_fields:
                        raise ValueError('Missing field: {}'.format(field))
                result = self.connector.set(self.local_node, data['key'],
                                            data['value'], data['timestamp'],
                                            data['expires'],
                                            data['created_with'],
                                            data['public_key'], data['name'],
                                            data['signature'])
                response = json.dumps(result)
                return web.Response(body=response.encode('utf-8'), status=200,
                                    content_type='application/json')
            else:
                raise ValueError('Wrong number of incoming fields!')
        except Exception as ex:
            log.error(ex)
            return web.HTTPBadRequest()

    @asyncio.coroutine
    def get_value(self, request):
        """
        GET to /<key> - gets a value from the referenced sha512 key.
        """
        # Get the sha512 key from the path.
        key = request.path[1:].lower()
        log.info('HTTP GET lookup for {}'.format(key))
        # Expect a single cache-control header with the value
        # no-cache in order to force an update.
        forced = False
        cache_control = [v.lower().strip() for k, v in request.headers.items()
                         if k.lower() == 'cache-control']
        if len(cache_control) == 1:
            forced = cache_control[0] == 'no-cache'
        data = self.connector.get(key, self.local_node, forced)
        result = json.dumps(data)
        return web.Response(body=result.encode('utf-8'), status=200)

    @asyncio.coroutine
    def get_static(self, request):
        """
        GET to /static/<path> returns static assets needed by the local node's
        web application user interface.
        """
        path = request.match_info['path']
        # Naively serve a binary file directly from the filesystem.
        file_path = os.path.join(self.resource_path, 'static', path)
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as static_file:
                static_content = static_file.read()
                return web.Response(body=static_content, status=200)
        else:
            raise web.HTTPNotFound()

    @asyncio.coroutine
    def web_soc(self, request):
        """
        Handles web-socket connections.
        """
        ws = web.WebSocketResponse()
        ws.start(request)
        while True:
            msg = yield from ws.receive()
            if msg.tp == aiohttp.MsgType.text:
                if msg.data == 'close':
                    yield from ws.close()
                else:
                    # TODO: handle incoming GET/SET calls.
                    pass
            elif msg.tp == aiohttp.MsgType.close:
                peer = request.transport.get_extra_info('peername')[0]
                log.info('Websocket with {} closed'.format(peer))
            elif msg.tp == aiohttp.MsgType.error:
                log.error('Websocket connection closed with error')
                log.error(ws.exception())
        return ws


def make_http_handler(event_loop, connector, local_node):
    """
    Returns a handler to be used when creating an asyncio server for the
    public facing web-application layer of the drogulus.

    The arguments are passed to the ApplicationHandler object.
    """
    app = web.Application()
    handler = ApplicationHandler(event_loop, connector, local_node)
    sha512_regex = r'{key:[a-zA-Z0-9]{128}$}'
    app.router.add_route('POST', '/', handler.dht_traffic)
    app.router.add_route('GET', '/', handler.home)
    app.router.add_route('POST', '/{}'.format(sha512_regex), handler.set_value)
    app.router.add_route('GET', '/{}'.format(sha512_regex), handler.get_value)
    app.router.add_route('GET', '/static/{path}', handler.get_static)
    app.router.add_route('GET', '/socket', handler.web_soc)
    return app.make_handler()
