# -*- coding: utf-8 -*-
"""
A rather silly test but added all the same for completeness and to check the
initial test suite works as expected.
"""
from drogulus.net.netstring import (NetstringProtocol, NetstringConnector,
                                    LENGTH)
from drogulus.dht.messages import OK, to_dict, from_dict
from drogulus.dht.contact import PeerNode
from drogulus.dht.crypto import get_seal
from drogulus.dht.node import Node
from drogulus.version import get_version
from ..dht.keys import PUBLIC_KEY, PRIVATE_KEY, BAD_PUBLIC_KEY
from hashlib import sha512
import unittest
import mock
import uuid
import json
import asyncio


class TestNetstringProtocol(unittest.TestCase):
    """
    Ensures the Netstring Protocol class works as expected.
    """

    def test_init(self):
        """
        Ensure the object is instantiated with the expected attributes.
        """
        p = NetstringProtocol('fake_connector', 'fake_node')
        self.assertEqual('fake_connector', p._connector)
        self.assertEqual('fake_node', p._node)
        length = 1024 * 1024 * 12
        self.assertEqual(p.MAX_LENGTH, length)
        self.assertEqual(p._reader_state, LENGTH)
        self.assertEqual(p._reader_length, 0)

    def test_connection_made(self):
        """
        Ensure the transport is correctly set when a connection is made.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made('abc')
        self.assertEqual('abc', p.transport)

    def test_data_received(self):
        """
        Ensure that good data results in the expected results:

        * No errors.
        * The correct call to string received.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello world,'.encode('utf-8'))
        p.string_received.assert_called_once_with('hello world')

    def test_string_received(self):
        """
        Ensure the string_received method works as expected.
        """
        transport = mock.MagicMock()
        transport.get_extra_info = mock.MagicMock(return_value='192.168.0.1')
        connector = mock.MagicMock()
        connector.receive = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.string_received('hello world')
        connector.receive.assert_called_once_with('hello world', '192.168.0.1',
                                                  node, p)

    def test_data_received_more_data(self):
        """
        Ensure that sequences of netstring from the remote peer are correctly
        handled.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello world,'.encode('utf-8'))
        p.data_received('11:hello world,'.encode('utf-8'))
        self.assertEqual(2, p.string_received.call_count)

    def test_data_received_in_chunks(self):
        """
        Ensure the netstring is re-constructed correctly if it is received
        over several calls to data_received (i.e. ensure the FSM is working).
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello '.encode('utf-8'))
        p.data_received('world,'.encode('utf-8'))
        p.string_received.assert_called_once_with('hello world')

    def test_data_received_containing_weird_unicode(self):
        """
        Ensure the netstring is re-constructed correctly if it contains weird
        unicode characters and a non-obvious length.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('15:zɐq ɹɐq ooɟ,'.encode('utf-8'))
        p.string_received.assert_called_once_with('zɐq ɹɐq ooɟ')

    def test_data_received_bad_end_character(self):
        """
        If the netstring does not terminate with a comma ensure that it is
        handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('11:hello world@'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_bad_length(self):
        """
        If the netstring does not start with an integer defining the length
        of the message then ensure the problem is handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('foo:hello world,'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_length_too_long(self):
        """
        If the netstring is expected to be too long then ensure the problem is
        handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('999999999999999999:hello world,'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_in_bad_state(self):
        """
        Ensure the correct RuntimeError is called if the state of the FSM is
        invalid.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p._reader_state = 4
        with self.assertRaises(RuntimeError):
            p.data_received('11:hello world@'.encode('utf-8'))

    def test_send_string(self):
        """
        Ensure the raw string form of the message is correctly turned into a
        valid netstring.
        """
        transport = mock.MagicMock()
        transport.write = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.send_string('foo bar baz')
        transport.write.assert_called_once_with(b'11:foo bar baz,')

    def test_send_utf8_string_with_correct_length(self):
        """
        Ensure the raw string containing weird unicode chars is correctly
        turned into a valid netstring with the correct length.
        """
        transport = mock.MagicMock()
        transport.write = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.send_string('zɐq ɹɐq ooɟ')
        length = len('zɐq ɹɐq ooɟ'.encode('utf-8'))
        expected = '%d:zɐq ɹɐq ooɟ,' % length
        transport.write.assert_called_once_with(expected.encode('utf-8'))


class TestNetstringConnector(unittest.TestCase):
    """
    Checks the NetstringConnector class works as expected.
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
        Check the class instantiates as expected.
        """
        nc = NetstringConnector(self.event_loop)
        self.assertEqual(nc._connections, {})
        self.assertEqual(nc.event_loop, self.event_loop)

    def test_send_message_with_protocol(self):
        """
        Ensures that the message is translated into a dictionary and passed
        into the protocol object in the expected way.
        """
        nc = NetstringConnector(self.event_loop)
        protocol = mock.MagicMock()
        protocol.send_string = mock.MagicMock()
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        nc._send_message_with_protocol(msg, protocol)
        protocol.send_string.assert_called_once_with({
            'message': 'ok',
            'uuid': 'uuid',
            'recipient': 'recipient',
            'sender': 'sender',
            'reply_port': 9999,
            'version': 'version',
            'seal': 'seal'
        })

    def test_send_with_cached_protocol(self):
        """
        Send the message to the referenced contact using a cached protocol
        object.
        """
        nc = NetstringConnector(self.event_loop)
        nc._send_message_with_protocol = mock.MagicMock()
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.1:1908')
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        protocol = mock.MagicMock()
        nc._connections[contact.network_id] = protocol
        result = nc.send(contact, msg)
        self.assertIsInstance(result, asyncio.Future)
        self.assertTrue(result.done())
        self.assertEqual(result.result(), True)
        nc._send_message_with_protocol.assert_called_once_with(msg, protocol)

    def test_send_with_failing_cached_protocol(self):
        """
        Attempting to send a message to the referenced contact using a
        cached protocol object that cannot send (e.g. perhaps the transport
        was dropped?) causes a retry as if the contact were new.
        """
        nc = NetstringConnector(self.event_loop)
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.1:1908')
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        protocol = mock.MagicMock()

        def side_effect(*args, **kwargs):
            raise ValueError()

        protocol.send_string = mock.MagicMock(side_effect=side_effect)
        nc._connections[contact.network_id] = protocol

        new_protocol = mock.MagicMock()
        new_protocol.send_string = mock.MagicMock()

        @asyncio.coroutine
        def faux_connect(protocol=new_protocol):
            return ('foo', protocol)

        with mock.patch.object(self.event_loop, 'create_connection',
                               return_value=faux_connect()):
            result = nc.send(contact, msg)
            self.event_loop.run_until_complete(result)
            self.assertEqual(1, new_protocol.send_string.call_count)
            self.assertTrue(result.done())
            self.assertEqual(True, result.result())
            self.assertIn(contact.network_id, nc._connections)
            self.assertEqual(nc._connections[contact.network_id],
                             new_protocol)
            m = to_dict(msg)
            new_protocol.send_string.assert_called_once_with(m)

    def test_send_to_new_contact_successful_connection(self):
        """
        Send a message to a new contact causes a new connection to be made
        whose associated protocol object is cached for later use.
        """
        nc = NetstringConnector(self.event_loop)
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.1:1908')
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        protocol = mock.MagicMock()
        protocol.send_string = mock.MagicMock()

        @asyncio.coroutine
        def faux_connect(protocol=protocol):
            return ('foo', protocol)

        with mock.patch.object(self.event_loop, 'create_connection',
                               return_value=faux_connect()):
            result = nc.send(contact, msg)
            self.event_loop.run_until_complete(result)
            self.assertEqual(1, protocol.send_string.call_count)
            self.assertTrue(result.done())
            self.assertEqual(True, result.result())
            self.assertIn(contact.network_id, nc._connections)
            self.assertEqual(nc._connections[contact.network_id], protocol)
            m = to_dict(msg)
            protocol.send_string.assert_called_once_with(m)

    def test_send_to_new_contact_failed_to_connect(self):
        """
        Sending a message to a new but unreachable contact results in the
        resulting deferred to be resolved with the expected exception.
        """
        nc = NetstringConnector(self.event_loop)
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.1:1908')
        msg = OK('uuid', 'recipient', 'sender', 9999, 'version', 'seal')
        protocol = mock.MagicMock()

        def side_effect(*args, **kwargs):
            raise ValueError()

        protocol.send_string = mock.MagicMock(side_effect=side_effect)

        @asyncio.coroutine
        def faux_connect(protocol=protocol):
            return ('foo', protocol)

        with mock.patch.object(self.event_loop, 'create_connection',
                               return_value=faux_connect()):
            result = nc.send(contact, msg)
            with self.assertRaises(ValueError) as ex:
                self.event_loop.run_until_complete(result)
            self.assertEqual(1, protocol.send_string.call_count)
            self.assertTrue(result.done())
            self.assertEqual(ex.exception, result.exception())
            self.assertNotIn(contact.network_id, nc._connections)

    def test_receive_valid_json_valid_message_from_new_peer(self):
        """
        A good message is received then the node handles the message as
        expected.
        """
        nc = NetstringConnector(self.event_loop)
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
        raw = json.dumps(ok)
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, nc, 1908)
        handler.message_received = mock.MagicMock()
        protocol = mock.MagicMock()
        nc.receive(raw, sender, handler, protocol)
        network_id = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        self.assertIn(network_id, nc._connections)
        self.assertEqual(nc._connections[network_id], protocol)
        msg = from_dict(ok)
        handler.message_received.assert_called_once_with(msg, 'netstring',
                                                         sender,
                                                         msg.reply_port)

    def test_receive_valid_json_valid_message_from_old_peer(self):
        """
        A good message is received then the node handles the message as
        expected. The cached protocol object for the peer node is expired since
        a new protocol object is used in this instance.
        """
        nc = NetstringConnector(self.event_loop)
        old_protocol = mock.MagicMock()
        network_id = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        nc._connections[network_id] = old_protocol

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
        raw = json.dumps(ok)
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, nc, 1908)
        handler.message_received = mock.MagicMock()
        protocol = mock.MagicMock()
        nc.receive(raw, sender, handler, protocol)
        self.assertIn(network_id, nc._connections)
        self.assertEqual(nc._connections[network_id], protocol)
        msg = from_dict(ok)
        handler.message_received.assert_called_once_with(msg, 'netstring',
                                                         sender,
                                                         msg.reply_port)

    def test_receive_invalid_json(self):
        """
        If a message is received that contains bad json then log the incident
        for later analysis.
        """
        patcher = mock.patch('drogulus.net.netstring.log.info')
        nc = NetstringConnector(self.event_loop)
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, nc, 1908)
        protocol = mock.MagicMock()
        raw = 'invalid JSON'
        mock_log = patcher.start()
        nc.receive(raw, sender, handler, protocol)
        self.assertEqual(3, mock_log.call_count)
        patcher.stop()

    def test_receive_valid_json_invalid_message(self):
        """
        If a message is received that consists of valid json but a malformed
        message then log the incident for later analysis.
        """
        patcher = mock.patch('drogulus.net.netstring.log.info')
        nc = NetstringConnector(self.event_loop)
        ping = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': BAD_PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(ping, PRIVATE_KEY)
        ping['seal'] = seal
        ping['message'] = 'ping'
        raw = json.dumps(ping)
        sender = '192.168.0.1'
        handler = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, nc, 1908)
        protocol = mock.MagicMock()
        mock_log = patcher.start()
        nc.receive(raw, sender, handler, protocol)
        self.assertEqual(3, mock_log.call_count)
        patcher.stop()
