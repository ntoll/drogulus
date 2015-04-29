# -*- coding: utf-8 -*-
"""
Contains the classes used to implement HTTP connectivity. These classes
handle the network communication "down the wire" in a way that is opaque to
the local node (from its point of view, messages come in and messages go out).
"""
from ..dht.messages import to_dict, from_dict
from .connector import Connector
from aiohttp import web
from aiohttp import protocol
import aiohttp
import aiohttp.server
import logging
import asyncio
import json
import traceback
import re
import time
import rsa
import binascii
import jinja2
import os


log = logging.getLogger(__name__)


def accept_request(request, allowed):
    """
    Returns True if the incoming request is to be accepted, otherwise False.

    Given an incoming HTTP 1.1 request will extract the appropriate
    'Authorization' and 'Validation' header values and ensure they relate to
    an entry in the whitelist of allowed clients who may use the node to
    GET/SET to the drogulus.

    The mechanism is simple:

    * The Authorization value is a SHA512 of the public key of the user who
    signed the incoming message.
    * The Validation value is an RSA signature (generated with the user's
    private key) of the path.
    * If an Authorization value is matched in the allowed whitelist of public
    keys then the Validation value is verified with the associated public
    key.
    * If the Validation is signed correctly then the return value is True.
    * In all other cases, the return value is False.

    The allowed argument is a dictionary where the keys are SHA512 hashes of
    their associated value - a string representation of the related public
    key used to verify invoming Validation values.
    """
    if request.version != protocol.HttpVersion11:
        return False
    authorization = request.headers.get('AUTHORIZATION', False)
    validation = request.headers.get('VALIDATION', False)
    if authorization and validation:
        if authorization in allowed:
            public_key = allowed[authorization]
            try:
                signature = binascii.unhexlify(validation.encode('ascii'))
                return rsa.verify(request.path.encode('ascii'), signature,
                                  allowed[authorization])
            except Exception as ex:
                log.error('Incoming request disallowed.')
                log.error(request)
                log.error(ex)
    return False


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


class ApplicationHandler:
    """
    A class that defines the methods to handle specific HTTP ACTION/PATH
    combinations.
    """

    def __init__(self, event_loop, connector, local_node, allowed):
        """
        The event loop, connector, local_node and allowed arguments are all
        stored as instance attributes to be referenced by the coroutine
        methods.
        """
        self.event_loop = event_loop
        self.connector = connector
        self.local_node = local_node
        self.allowed = allowed
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
            raw_data = yield from request.json()
            peer = self.transport.get_extra_info('peername')[0]
            log.info(peer)
            log.info(raw_data)
            result = yield from self.connector.receive(raw_data, peer,
                                                       self.local_node)
            data = to_dict(result)
        except Exception as ex:
            # We log any errors in the connector / node instances,
            # so return an appropriate error to the caller.
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
    def set_value(self, request, key):
        """
        POST to /<key> - sets a value to the referenced sha512 key.
        """
        return web.HTTPForbidden()
        pass

    @asyncio.coroutine
    def get_value(self, request, key):
        """
        GET to /<key> - gets a value from the referenced sha512 key.
        """
        pass

    @asyncio.coroutine
    def get_static(self, request):
        """
        GET to /static/<path> returns static assets needed by the local node's
        web application user interface.
        """
        template_extensions = ('html')
        path = request.match_info['path']
        if path.endswith(template_extensions):
            template_name = 'static/{}'.format(path)
            if template_name in self.template_env.list_templates():
                template = self.template_env.get_template(template_name)
                return web.Response(body=template.render().encode('utf-8'),
                                    status=200)
            else:
                raise web.HTTPNotFound()
        else:
            # Naively serve a binary file directly from the filesystem.
            file_path = os.path.join(self.resource_path, 'static', path)
            if os.path.isfile(file_path):
                static_file = open(file_path, 'rb').read()
                return web.Response(body=static_file, status=200)
            else:
                raise web.HTTPNotFound()

    @asyncio.coroutine
    def web_soc(request):
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
            elif msg.tp == aiohttpMsgType.close:
                peer = self.transport.get_extra_info('peername')[0]
                log.info('Websocket with {} closed'.format(peer))
            elif msg.tp == aiohttpMsgType.error:
                log.error('Websocket connection closed with error')
                log.error(ws.exception())
        return ws


def make_http_handler(event_loop, connector, local_node, allowed):
    """
    Returns a handler to be used when creating an asyncio server for the
    public facing web-application layer of the drogulus.

    The arguments are passed to the ApplicationHandler object.
    """
    app = web.Application()
    handler = ApplicationHandler(event_loop, connector, local_node, allowed)
    sha512_regex = r'{key:[a-zA-Z0-9]{128}$}'
    app.router.add_route('POST', '/', handler.dht_traffic)
    app.router.add_route('GET', '/', handler.home)
    app.router.add_route('POST', '/{}'.format(sha512_regex), handler.set_value)
    app.router.add_route('GET', '/{}'.format(sha512_regex), handler.get_value)
    app.router.add_route('GET', '/static/{path}', handler.get_static)
    app.router.add_route('GET', '/socket', handler.web_soc)
    return app.make_handler()


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
