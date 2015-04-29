# -*- coding: utf-8 -*-
"""
Ensures that the HTTP Protocol and Connector classes work as expected.
"""
from drogulus.net.http import (HttpConnector, accept_request,
                               ApplicationHandler, make_http_handler,
                               HttpRequestHandler)
from drogulus.dht.messages import OK, to_dict, from_dict
from drogulus.dht.contact import PeerNode
from drogulus.dht.crypto import get_seal
from drogulus.dht.node import Node
from drogulus.version import get_version
from ..keys import PUBLIC_KEY, PRIVATE_KEY
from unittest import mock
from hashlib import sha512
from uuid import uuid4
from aiohttp import protocol
from aiohttp import web
import time
import hashlib
import json
import uuid
import asyncio
import aiohttp
import unittest
import rsa
import binascii


(PUBKEY, PRIVKEY) = rsa.newkeys(1024)


class TestAcceptRequest(unittest.TestCase):
    """
    Ensures that the accept_request function exhibits the correct behaviour
    for incoming requests.
    """

    def setUp(self):
        """
        Recreate a new incoming request each time..!
        """
        # A valid request
        request = mock.MagicMock()
        path_hash = sha512(str(uuid4()).encode('ascii')).hexdigest()
        request.path = '/{}'.format(path_hash)
        headers = {}
        pubkey_hash = sha512(PUBKEY.save_pkcs1()).hexdigest()
        headers['AUTHORIZATION'] = pubkey_hash
        signature = rsa.sign(request.path.encode('ascii'), PRIVKEY, 'SHA-512')
        headers['VALIDATION'] = binascii.hexlify(signature).decode('ascii')
        request.headers = headers
        request.version = protocol.HttpVersion11
        self.request = request
        # An allowed dictionary containing the correct public key.
        self.allowed = {
            pubkey_hash: PUBKEY,
        }

    def test_valid_request_with_matched_key(self):
        """
        The incoming request has the correct headers containing an
        Authorization value that matches with the allowed whitelist and a
        related Validation value that verifies.

        This is the only case where the function should return True.
        """
        self.assertTrue(accept_request(self.request, self.allowed))

    def test_http_version_is_not_1_1(self):
        """
        If the HTTP version is not 1.1 return False.
        """
        self.request.version = protocol.HttpVersion10
        self.assertFalse(accept_request(self.request, self.allowed))

    def test_valid_request_with_unmatched_key(self):
        """
        The request is correct (it has the right headers) but does not match
        the allowed whitelist.
        """
        self.allowed = {}
        self.assertFalse(accept_request(self.request, self.allowed))

    def test_valid_request_with_matched_key_invalid_validation(self):
        """
        The key is matched but the validation check fails.
        """
        self.request.headers['VALIDATION'] = 'foo'
        self.assertFalse(accept_request(self.request, self.allowed))

    def test_request_missing_authorization_header(self):
        """
        The request fails since it does not contain the required Authorization
        header.
        """
        del self.request.headers['AUTHORIZATION']
        self.assertFalse(accept_request(self.request, self.allowed))

    def test_request_missing_validation_header(self):
        """
        The request fails since it does not contain the required Validation
        header.
        """
        del self.request.headers['VALIDATION']
        self.assertFalse(accept_request(self.request, self.allowed))


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
        event_loop = mock.MagicMock()
        event_loop.call_later = mock.MagicMock()
        connector = HttpConnector(event_loop)
        self.assertEqual({}, connector.lookups)
        self.assertEqual(event_loop, connector.event_loop)
        sweep = connector._sweep_and_clean_cache
        event_loop.call_later.assert_called_once_with(300, sweep, event_loop,
                                                      300)

    def test_sweep_and_clean_cache_fresh_items_only(self):
        """
        If the lookup cache is only full of fresh items then the cache remains
        the same (nothing to delete).
        """
        event_loop = mock.MagicMock()
        connector = HttpConnector(event_loop)
        event_loop.call_later = mock.MagicMock()
        now = time.time()
        for i in range(10):
            connector.lookups[str(i)] = {
                'last_access': now,
                'lookup': mock.MagicMock()
            }
        connector._sweep_and_clean_cache(event_loop, 300)
        self.assertEqual(len(connector.lookups), 10)

    def test_sweep_and_clean_cache_stale_items_only(self):
        """
        If the lookup cache is only full of stale items then the cache should
        be emtied.
        """
        event_loop = mock.MagicMock()
        connector = HttpConnector(event_loop)
        event_loop.call_later = mock.MagicMock()
        now = time.time()
        for i in range(10):
            connector.lookups[str(i)] = {
                'last_access': now - 500,
                'lookup': mock.MagicMock()
            }
        connector._sweep_and_clean_cache(event_loop, 300)
        self.assertEqual(len(connector.lookups), 0)

    def test_sweep_and_clean_cache_mixed_fresh_and_stale_items(self):
        """
        Only the stale items should be removed from the cache.
        """
        event_loop = mock.MagicMock()
        connector = HttpConnector(event_loop)
        event_loop.call_later = mock.MagicMock()
        now = time.time()
        for i in range(10):
            if i % 2:
                access = now - 500
            else:
                access = now
            connector.lookups[str(i)] = {
                'last_access': access,
                'lookup': mock.MagicMock()
            }
        connector._sweep_and_clean_cache(event_loop, 300)
        self.assertEqual(len(connector.lookups), 5)

    def test_sweep_and_clean_cache_schedules_again(self):
        """
        Sweep and clean should schedule a new sweep and clean in
        clean_interval seconds.
        """
        event_loop = mock.MagicMock()
        connector = HttpConnector(event_loop)
        event_loop.call_later = mock.MagicMock()
        connector._sweep_and_clean_cache(event_loop, 300)
        sweep = connector._sweep_and_clean_cache
        event_loop.call_later.assert_called_once_with(300, sweep, event_loop,
                                                      300)

    def test_init_with_bespoke_clean_interval(self):
        """
        Ensures that a custom clean_interval value is used when scheduling the
        _sweep_and_clean_cache method.
        """
        event_loop = mock.MagicMock()
        event_loop.call_later = mock.MagicMock()
        connector = HttpConnector(event_loop, 900)
        self.assertEqual({}, connector.lookups)
        self.assertEqual(event_loop, connector.event_loop)
        sweep = connector._sweep_and_clean_cache
        event_loop.call_later.assert_called_once_with(900, sweep, event_loop,
                                                      900)

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
        self.assertIsInstance(connector.lookups[test_key]['last_access'],
                              float)
        self.assertEqual(connector.lookups[test_key]['lookup'], faux_lookup)
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
        connector.lookups[test_key] = {
            'last_access': 123.45,
            'lookup': faux_lookup
        }
        result = connector.get(test_key, handler)
        self.assertIn(test_key, connector.lookups)
        # Check the last_access has been updated
        self.assertTrue(connector.lookups[test_key]['last_access'] > 123.45)
        self.assertEqual(connector.lookups[test_key]['lookup'], faux_lookup)
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
        connector.lookups[test_key] = {
            'last_access': 123.45,
            'lookup': faux_lookup
        }
        result = connector.get(test_key, handler)
        self.assertIn(test_key, connector.lookups)
        self.assertTrue(connector.lookups[test_key]['last_access'] > 123.45)
        self.assertEqual(connector.lookups[test_key]['lookup'], faux_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], faux_lookup._state.lower())
        self.assertEqual(result['error'], True)
        self.assertEqual(3, len(result))

    def test_get_forced_refresh_existing_value(self):
        """
        Ensures that an existing result is ignored and a new lookup is executed
        if the 'forced' flag is True.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        cached_lookup = asyncio.Future()
        cached_lookup.set_result('foo')
        test_key = hashlib.sha512().hexdigest()
        connector.lookups[test_key] = cached_lookup
        new_lookup = asyncio.Future()
        handler.retrieve = mock.MagicMock(return_value=new_lookup)
        result = connector.get(test_key, handler, forced=True)
        self.assertIn(test_key, connector.lookups)
        self.assertIsInstance(connector.lookups[test_key]['last_access'],
                              float)
        self.assertEqual(connector.lookups[test_key]['lookup'], new_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], new_lookup._state.lower())
        self.assertEqual(2, len(result))

    def test_get_forced_refresh_no_existing_cached_value(self):
        """
        Ensures that even if there's no cached value a new lookup is executed
        if the 'forced' flag is True.
        """
        connector = HttpConnector(self.event_loop)
        self.assertEqual({}, connector.lookups)
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, connector,
                       1908)
        faux_lookup = asyncio.Future()
        handler.retrieve = mock.MagicMock(return_value=faux_lookup)
        test_key = hashlib.sha512().hexdigest()
        result = connector.get(test_key, handler, forced=True)
        handler.retrieve.assert_called_once_with(test_key)
        self.assertIn(test_key, connector.lookups)
        self.assertIsInstance(connector.lookups[test_key]['last_access'],
                              float)
        self.assertEqual(connector.lookups[test_key]['lookup'], faux_lookup)
        self.assertEqual(result['key'], test_key)
        self.assertEqual(result['status'], faux_lookup._state.lower())
        self.assertEqual(2, len(result))


class TestApplicationHandler(unittest.TestCase):
    """
    Ensures that the ApplicationHandler class works as expected.

    The ApplicationHandler defines the methods that handle specific HTTP
    ACTION/PATH combinations.
    """

    def setUp(self):
        """
        Set up a new throw-away event loop.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        pubkey_hash = sha512(PUBKEY.save_pkcs1()).hexdigest()
        self.event_loop = asyncio.get_event_loop()
        self.connector = HttpConnector(self.event_loop)
        self.local_node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop,
                               self.connector, 1908)
        self.allowed = {pubkey_hash: PUBKEY}

    def test_init(self):
        """
        Check that the passed in arguments really *are* set against the
        local instance.
        """
        ah = ApplicationHandler(self.event_loop, self.connector,
                                self.local_node, self.allowed)
        self.assertEqual(ah.event_loop, self.event_loop)
        self.assertEqual(ah.connector, self.connector)
        self.assertEqual(ah.local_node, self.local_node)
        self.assertEqual(ah.allowed, self.allowed)

    def test_dht_traffic(self):
        """
        Ensure that all DHT related traffic is handled as expected.
        """
        fake_connector = HttpConnector(self.event_loop)
        fake_result = OK('uuid', 'recipient', 'sender', 9999, 'version',
                         'seal')

        @asyncio.coroutine
        def faux_receive(*args, **kwargs):
            return fake_result

        fake_connector.receive = mock.MagicMock(side_effect=faux_receive)
        ah = ApplicationHandler(self.event_loop, fake_connector,
                                self.local_node, self.allowed)

        ah.transport = mock.MagicMock()
        peer = ('192.168.0.1', 8888)
        ah.transport.get_extra_info = mock.MagicMock(return_value=peer)
        mockRequest = mock.MagicMock()

        @asyncio.coroutine
        def faux_json(*args, **kwargs):
            return {'some', 'json'}

        mockRequest.json = mock.MagicMock(side_effect=faux_json)

        with mock.patch.object(web, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(ah.dht_traffic(mockRequest))
            expected_body = json.dumps(to_dict(fake_result)).encode('utf-8')
            response.assert_called_once_with(body=expected_body, status=200,
                                             content_type='application/json')

    def test_dht_traffic_with_error(self):
        """
        Ensure that DHT related traffic that causes an error is handled as
        expected.
        """
        fake_connector = HttpConnector(self.event_loop)

        @asyncio.coroutine
        def faux_receive(*args, **kwargs):
            raise Exception('Bang')

        fake_connector.receive = mock.MagicMock(side_effect=faux_receive)
        ah = ApplicationHandler(self.event_loop, fake_connector,
                                self.local_node, self.allowed)

        ah.transport = mock.MagicMock()
        peer = ('192.168.0.1', 8888)
        ah.transport.get_extra_info = mock.MagicMock(return_value=peer)
        mockRequest = mock.MagicMock()

        @asyncio.coroutine
        def faux_json(*args, **kwargs):
            return {'some', 'json'}

        mockRequest.json = mock.MagicMock(side_effect=faux_json)
        self.event_loop.set_exception_handler(mock.MagicMock())
        with self.assertRaises(web.HTTPInternalServerError):
            self.event_loop.run_until_complete(ah.dht_traffic(mockRequest))

    def test_home(self):
        """
        Ensure the HTML for the local node's homepage is returned.
        """
        ah = ApplicationHandler(self.event_loop, self.connector,
                                self.local_node, self.allowed)
        mockRequest = mock.MagicMock()
        template = mock.MagicMock()
        template.render = mock.MagicMock(return_value='<html/>')
        ah.template_env.get_template = mock.MagicMock(return_value=template)
        with mock.patch.object(web, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(ah.home(mockRequest))
            network_id = self.local_node.network_id
            template.render.assert_called_once_with(node_id=network_id)
            expected_body = template.render().encode('utf-8')
            response.assert_called_once_with(body=expected_body, status=200)

    def test_set_value(self):
        """
        Ensures a POST to /<key> is handled correctly.
        """
        assert False

    def test_get_value(self):
        """
        Ensures a GET to /<key> is handled correctly.
        """
        assert False

    def test_get_static_not_found(self):
        """
        Ensures GET requests to an unknown /static/<path> are handled
        correctly.
        """
        ah = ApplicationHandler(self.event_loop, self.connector,
                                self.local_node, self.allowed)
        mockRequest = mock.MagicMock()
        mockRequest.match_info = {
            'path': 'foo.js',
        }
        self.event_loop.set_exception_handler(mock.MagicMock())
        with self.assertRaises(web.HTTPNotFound):
            self.event_loop.run_until_complete(ah.get_static(mockRequest))

    def test_get_static(self):
        """
        Ensures GET requests to /static/<path> are handled correctly.
        """
        ah = ApplicationHandler(self.event_loop, self.connector,
                                self.local_node, self.allowed)
        mockRequest = mock.MagicMock()
        mockRequest.match_info = {
            'path': 'drogulus.js',
        }
        template = mock.MagicMock()
        template.render = mock.MagicMock(side_effect=lambda: '<html/>')
        ah.template_env.get_template = mock.MagicMock(return_value=template)
        with mock.patch.object(web, 'Response',
                               return_value=mock.MagicMock()) as response:
            self.event_loop.run_until_complete(ah.get_static(mockRequest))
            expected_body = template.render().encode('utf-8')
            response.assert_called_once_with(body=expected_body, status=200)


class TestMakeHttpHandler(unittest.TestCase):
    """
    Ensures the make_http_handler function works as expected.
    """

    def setUp(self):
        """
        Set up a new throw-away event loop.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        pubkey_hash = sha512(PUBKEY.save_pkcs1()).hexdigest()
        self.event_loop = asyncio.get_event_loop()
        self.connector = HttpConnector(self.event_loop)
        self.local_node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop,
                               self.connector, 1908)
        self.allowed = {pubkey_hash: PUBKEY}

    def test_make_http_handler(self):
        """
        Test the resulting handler is set up correctly (there should be 6
        paths to be "handled").
        """
        handler = make_http_handler(self.event_loop, self.connector,
                                    self.local_node, self.allowed)
        self.assertEqual(6, len(handler._app.router._urls))


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

    def test_handle_GET_no_cache(self):
        """
        Ensure that if the cache-control header in the request is set to
        no-cache then the lookup is foreced (i.e. don't use the local cache).
        """
        test_key = hashlib.sha512().hexdigest()
        mockMessage = mock.MagicMock()
        mockMessage.method = 'GET'
        mockMessage.version = '1.1'
        mockMessage.path = ''.join(['/', test_key])
        mockMessage.headers = {'Cache-Control': 'no-cache', }
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
            # The connector's get method was called with the forced flag set
            # to True.
            connector.get.assert_called_once_with(test_key, node, True)

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
