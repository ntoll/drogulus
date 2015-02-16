# -*- coding: utf-8 -*-
"""
Ensures that the HTTP Protocol and Connector classes work as expected.
"""
from drogulus.net.http import HttpConnector, HttpRequestHandler
from drogulus.dht.messages import OK, to_dict, from_dict
from drogulus.dht.contact import PeerNode
from drogulus.dht.crypto import get_seal
from drogulus.dht.node import Node
from drogulus.version import get_version
from ..keys import PUBLIC_KEY, PRIVATE_KEY
from unittest import mock
import hashlib
import json
import uuid
import asyncio
import aiohttp
import unittest


class TestHttpConnector(unittest.TestCase):
    """
    Ensures that the HttpConnector class defines the correct behaviour for
    sending and receiving data over the network.
    """

    def setUp(self):
        """
        Set up a new throw-away event loop.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        self.version = get_version()

    def tearDown(self):
        """
        Clean up the event loop.
        """
        self.event_loop.close()

    def test_init(self):
        """
        Ensure the instance has an empty lookups dict assigned and a sweep and
        clean of the lookups cache is scheduled after X seconds.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)

    def test_send(self):
        """
        Test the good case. We should end up with a task wrapping an
        appropriate call to aiohttp.request.
        """
        contact = PeerNode(PUBLIC_KEY, self.version, 'http://192.168.0.1:80')
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        msg_json = json.dumps(to_dict(msg))
        headers = {'content-type': 'application/json'}
        connector = HttpConnector(self.event_loop)

        @asyncio.coroutine
        def faux_request(*args, **kwargs):
            return 'foo'

        with mock.patch.object(aiohttp, 'request',
                               return_value=faux_request()) as request:
            result = connector.send(contact, msg)
            self.assertIsInstance(result, asyncio.Task)
            request.assert_called_once_with('post', contact.uri, data=msg_json,
                                            headers=headers)

    def test_receive(self):
        """
        The good case. Should return whatever handler.message_received
        returns.
        """
        connector = HttpConnector(self.event_loop)
        ok = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(ok, PRIVATE_KEY)
        ok['seal'] = seal
        ok['message'] = 'ok'
        raw = json.dumps(ok).encode('utf-8')
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        handler.message_received = mock.MagicMock()
        connector.receive(raw, sender, handler)
        msg = from_dict(ok)
        handler.message_received.assert_called_once_with(msg, 'http',
                                                         sender,
                                                         msg.reply_port)

    def test_receive_not_json(self):
        """
        Appropriately handle a message that doesn't contain JSON.
        """
        patcher = mock.patch('drogulus.net.http.log.error')
        connector = HttpConnector(self.event_loop)
        raw = "junk from the network".encode('utf-8')
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        mock_log = patcher.start()
        self.assertRaises(ValueError, connector.receive, raw, sender, handler)
        self.assertEqual(4, mock_log.call_count)
        patcher.stop()

    def test_receive_bad_message(self):
        """
        Appropriately handle a message that is valid JSON but not a valid
        message type understood as part of the drogulus protocol.
        """
        patcher = mock.patch('drogulus.net.http.log.error')
        connector = HttpConnector(self.event_loop)
        ok = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        raw = json.dumps(ok).encode('utf-8')
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        mock_log = patcher.start()
        self.assertRaises(KeyError, connector.receive, raw, sender, handler)
        self.assertEqual(4, mock_log.call_count)
        patcher.stop()

    def test_get_new_lookup(self):
        """
        Getting an unknown key fires a new lookup that is initially produces a
        'pending' status.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        faux_lookup = asyncio.Future()
        handler.retrieve = mock.MagicMock(return_value=faux_lookup)
        test_key = hashlib.sha512().hexdigest()
        result = connector.get(test_key, handler)
        handler.retrieve.assert_called_once_with(test_key)
        self.assertIn(test_key, connector.lookups)
        self.assertEqual(connector.lookups[test_key], faux_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], faux_lookup._state.lower())
        self.assertEqual(2, len(result))

    def test_get_existing_lookup(self):
        """
        Getting an existing key that has completed returns a 'finished' status
        and associated value.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        faux_lookup = asyncio.Future()
        faux_lookup.set_result('foo')
        test_key = hashlib.sha512().hexdigest()
        connector.lookups[test_key] = faux_lookup
        result = connector.get(test_key, handler)
        self.assertIn(test_key, connector.lookups)
        self.assertEqual(connector.lookups[test_key], faux_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], faux_lookup._state.lower())
        self.assertEqual(result['value'], 'foo')
        self.assertEqual(3, len(result))

    def test_get_existing_lookup_failed(self):
        """
        Getting an existing key that has resulted in an error returns a
        'finished' status and an 'error' flag.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        faux_lookup = asyncio.Future()
        ex = Exception('Bang!')
        faux_lookup.set_exception(ex)
        test_key = hashlib.sha512().hexdigest()
        connector.lookups[test_key] = faux_lookup
        result = connector.get(test_key, handler)
        self.assertIn(test_key, connector.lookups)
        self.assertEqual(connector.lookups[test_key], faux_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], faux_lookup._state.lower())
        self.assertEqual(result['error'], True)
        self.assertEqual(3, len(result))


class TestHttpRequestHandler(unittest.TestCase):
    """
    Ensure the HttpRequestHandler is instantiated correctly, only handles
    POST requests and handles all other incoming requests in a safe manner.
    """

    def setUp(self):
        """
        Set up a new throw-away event loop.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        self.version = get_version()

    def tearDown(self):
        """
        Clean up the event loop.
        """
        self.event_loop.close()

    def test_init_(self):
        """
        The connector and node instances should be set properly.
        """
        connector = HttpConnector(self.event_loop)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node)
        self.assertEqual(connector, hrh.connector)
        self.assertEqual(node, hrh.node)

    def test_init_with_extra_kwargs(self):
        """
        An further arguments passed in (above and beyond the connector and node
        instances) are correctly handled.
        """
        connector = HttpConnector(self.event_loop)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        self.assertEqual(connector, hrh.connector)
        self.assertEqual(node, hrh.node)
        self.assertEqual(True, hrh.debug)

    def test_handle_POST_request(self):
        """
        A valid POST request causes a 200 response.

        * WARNING * Too much mocking going on here (in the vain attempt to
        achieve 100% test coverage).
        """
        mockMessage = mock.MagicMock()
        mockMessage.method = 'POST'
        mockMessage.version = '1.1'
        mockPayload = mock.MagicMock()

        @asyncio.coroutine
        def faux_read(*args, **kwargs):
            return 'raw_data'

        mockPayload.read = mock.MagicMock(side_effect=faux_read)
        connector = HttpConnector(self.event_loop)

        def faux_receive(*args, **kwargs):
            return OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')

        connector.receive = mock.MagicMock(side_effect=faux_receive)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        peer = '192.168.0.1'
        hrh.transport = mock.MagicMock()
        hrh.transport.get_extra_info = mock.MagicMock(side_effect=peer)
        hrh.writer = mock.MagicMock()

        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  mockPayload))
            response.assert_called_once_with(hrh.writer, 200,
                                             http_version=mockMessage.version)

    def test_handle_GET_request(self):
        """
        A valid GET request casues a 200 reponse.
        """
        test_key = hashlib.sha512().hexdigest()
        mockMessage = mock.MagicMock()
        mockMessage.method = 'GET'
        mockMessage.version = '1.1'
        mockMessage.path = ''.join(['/', test_key])
        connector = HttpConnector(self.event_loop)

        def faux_get(*args, **kwargs):
            return {
                'key': test_key,
                'status': 'pending',
            }

        connector.get = mock.MagicMock(side_effect=faux_get)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        peer = '192.168.0.1'
        hrh.transport = mock.MagicMock()
        hrh.transport.get_extra_info = mock.MagicMock(side_effect=peer)
        hrh.writer = mock.MagicMock()
        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  None))
            response.assert_called_once_with(hrh.writer, 200,
                                             http_version=mockMessage.version)

    def test_handle_GET_bad_request(self):
        """
        A GET request without a valid sha512 hexdigest as its path causes a
        400 (Bad Request) response.
        """
        test_key = 'not_a_valid_sha512_hexdigest'
        mockMessage = mock.MagicMock()
        mockMessage.method = 'GET'
        mockMessage.version = '1.1'
        mockMessage.path = ''.join(['/', test_key])
        connector = HttpConnector(self.event_loop)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        hrh.writer = mock.MagicMock()
        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  None))
            response.assert_called_once_with(hrh.writer, 400,
                                             http_version=mockMessage.version)

    def test_handle_GET_internal_server_error(self):
        """
        A GET request that causes an exception simply returns a 500 (Internal
        Server Error).
        """
        test_key = hashlib.sha512().hexdigest()
        mockMessage = mock.MagicMock()
        mockMessage.method = 'GET'
        mockMessage.version = '1.1'
        mockMessage.path = ''.join(['/', test_key])
        connector = HttpConnector(self.event_loop)

        def faux_get(*args, **kwargs):
            raise Exception('Bang!')

        connector.get = mock.MagicMock(side_effect=faux_get)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        peer = '192.168.0.1'
        hrh.transport = mock.MagicMock()
        hrh.transport.get_extra_info = mock.MagicMock(side_effect=peer)
        hrh.writer = mock.MagicMock()
        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  None))
            response.assert_called_once_with(hrh.writer, 500,
                                             http_version=mockMessage.version)

    def test_handle_request_not_POST_or_GET(self):
        """
        A request that is not a POST causes a 405 response.
        """
        mockMessage = mock.MagicMock()
        mockMessage.method = 'PUT'
        mockMessage.version = '1.1'
        mockPayload = mock.MagicMock()
        connector = HttpConnector(self.event_loop)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        hrh.writer = mock.MagicMock()

        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  mockPayload))
            response.assert_called_once_with(hrh.writer, 405,
                                             http_version=mockMessage.version)

    def test_handle_request_causes_exception(self):
        """
        A request that raises an exception causes a 500 response.
        """
        mockMessage = mock.MagicMock()
        mockMessage.method = 'POST'
        mockMessage.version = '1.1'
        mockPayload = mock.MagicMock()

        @asyncio.coroutine
        def faux_read(*args, **kwargs):
            return 'raw_data'

        mockPayload.read = mock.MagicMock(side_effect=faux_read)
        connector = HttpConnector(self.event_loop)

        def faux_receive(*args, **kwargs):
            raise ValueError('Boom! Something went wrong.')

        connector.receive = mock.MagicMock(side_effect=faux_receive)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector, 1908)
        hrh = HttpRequestHandler(connector, node, debug=True)
        peer = '192.168.0.1'
        hrh.transport = mock.MagicMock()
        hrh.transport.get_extra_info = mock.MagicMock(side_effect=peer)
        hrh.writer = mock.MagicMock()

        with mock.patch.object(aiohttp, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(hrh.handle_request(mockMessage,
                                                                  mockPayload))
            response.assert_called_once_with(hrh.writer, 500,
                                             http_version=mockMessage.version)
