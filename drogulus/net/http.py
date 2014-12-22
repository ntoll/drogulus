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


log = logging.getLogger(__name__)


class HttpConnector(Connector):
    """
    A connector child class that brokers between the HTTP network-y end
    of things and the local node within the DHT network.
    """

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

    def receive(self, raw, sender, handler):
        """
        Called when a message is received from a remote node on the network.
        """
        try:
            message_dict = json.loads(raw)
            message = from_dict(message_dict)
            return handler.message_received(message, 'http', sender,
                                            message.reply_port)
        except Exception as ex:
            # There's not a lot that can be usefully done at this stage except
            # to log the problem in a way that may aid further investigation.
            log.error('Problem message received from {}'.format(sender))
            log.exception(ex)
            log.error(raw)
            # Will cause generic 5** HTTP error response.
            raise ex


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
                result = self.connector.receive(raw_data, peer, self.node)
                data = to_dict(result)
                response_code = 200  # OK
            except:
                # We log any errors in the connector / node instances so,
                # nothing to do here but return an error message to the
                # client.
                response_code = 500  # Internal Server Error
        raw_output = json.dumps(data).encode('utf-8')
        headers['Content-Length'] = len(raw_output)
        response = aiohttp.Response(self.writer, response_code,
                                    http_version=message.version)
        for k, v in headers.items():
            response.add_header(k, v)
        response.send_headers()
        response.write(raw_output)
        yield from response.write_eof()
