# -*- coding: utf-8 -*-
"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import Node
from drogulus.dht.constants import ERRORS
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus.dht.net import DHTFactory
from drogulus.dht.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value)
from drogulus.dht.crypto import construct_key
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.python import log
from mock import MagicMock
from uuid import uuid4
import time
import re


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQ
LN2RbbDIMHILA1i6wByXkqEamnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjG
b+oGVTKizfbMbGCKZ8fT64ZZgan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M
6WixkMTbFM91fW0mUwIDAQAB
-----END PUBLIC KEY-----"""


class TestNode(unittest.TestCase):
    """
    Ensures the Node class works as expected.
    """

    def setUp(self):
        """
        Following the pattern explained here:

        http://twistedmatrix.com/documents/current/core/howto/trial.html
        """
        self.node_id = '1234567890abc'
        self.node = Node(self.node_id)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)
        self.value = 'value'
        self.signature = ('\x882f\xf9A\xcd\xf9\xb1\xcc\xdbl\x1c\xb2\xdb' +
                          '\xa3UQ\x9a\x08\x96\x12\x83^d\xd8M\xc2`\x81Hz' +
                          '\x84~\xf4\x9d\x0e\xbd\x81\xc4/\x94\x9dfg\xb2aq' +
                          '\xa6\xf8!k\x94\x0c\x9b\xb5\x8e \xcd\xfb\x87' +
                          '\x83`wu\xeb\xf2\x19\xd6X\xdd\xb3\x98\xb5\xbc#B' +
                          '\xe3\n\x85G\xb4\x9c\x9b\xb0-\xd2B\x83W\xb8\xca' +
                          '\xecv\xa9\xc4\x9d\xd8\xd0\xf1&\x1a\xfaw\xa0\x99' +
                          '\x1b\x84\xdad$\xebO\x1a\x9e:w\x14d_\xe3\x03#\x95' +
                          '\x9d\x10B\xe7\x13')
        self.uuid = str(uuid4())
        self.timestamp = 1350544046.084875
        self.expires = 1352221970.14242
        self.name = 'name'
        self.meta = {'meta': 'value'}
        self.version = get_version()
        self.key = construct_key(PUBLIC_KEY, self.name)

    def test_init(self):
        """
        Ensures the class is instantiated correctly.
        """
        node = Node(123)
        self.assertEqual(123, node.id)
        self.assertTrue(node._routing_table)
        self.assertEqual({}, node._data_store)
        self.assertEqual(get_version(), node.version)

    def test_except_to_error_with_exception_args(self):
        """
        Ensure an exception created by drogulus (that includes meta-data in
        the form of exception args) is correctly transformed into an Error
        message instance.
        """
        uuid = str(uuid4())
        details = {'context': 'A message'}
        ex = ValueError(1, ERRORS[1], details, uuid)
        result = self.node.except_to_error(ex)
        self.assertEqual(uuid, result.uuid)
        self.assertEqual(self.node.id, result.node)
        self.assertEqual(1, result.code)
        self.assertEqual(ERRORS[1], result.title)
        self.assertEqual(details, result.details)

    def test_except_to_error_with_regular_exception(self):
        """
        Ensure that a generic Python exception is correctly transformed in to
        an Error message instance.
        """
        ex = ValueError('A generic exception')
        result = self.node.except_to_error(ex)
        self.assertEqual(self.node.id, result.node)
        self.assertEqual(3, result.code)
        self.assertEqual(ERRORS[3], result.title)
        self.assertEqual({}, result.details)
        uuidMatch = ('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-' +
                     '[a-f0-9]{12}')
        self.assertTrue(re.match(uuidMatch, result.uuid))

    def test_except_to_error_with_junk(self):
        """
        Given that this is a function that cannot fail it must be able to cope
        with input that is not an Exception. A sanity check for some defensive
        programming.
        """
        result = self.node.except_to_error('foo')
        self.assertEqual(self.node.id, result.node)
        self.assertEqual(3, result.code)
        self.assertEqual(ERRORS[3], result.title)
        self.assertEqual({}, result.details)
        uuidMatch = ('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-' +
                     '[a-f0-9]{12}')
        self.assertTrue(re.match(uuidMatch, result.uuid))

    def test_message_received_calls_routing_table(self):
        """
        Ensures an inbound message updates the routing table.
        """
        self.node._routing_table.add_contact = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the routing table's add_contact method.
        peer = self.protocol.transport.getPeer()
        self.assertEqual(1, self.node._routing_table.add_contact.call_count)
        arg1 = self.node._routing_table.add_contact.call_args[0][0]
        self.assertTrue(isinstance(arg1, Contact))
        self.assertEqual(msg.node, arg1.id)
        self.assertEqual(peer.host, arg1.address)
        self.assertEqual(peer.port, arg1.port)
        self.assertEqual(msg.version, arg1.version)
        self.assertTrue(isinstance(arg1.last_seen, float))

    def test_message_received_ping(self):
        """
        Ensures a Ping message is handled correctly.
        """
        self.node.handle_ping = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_ping method.
        self.node.handle_ping.assert_called_once_with(msg, self.protocol)

    def test_message_received_store(self):
        """
        Ensures a Store message is handled correctly.
        """
        self.node.handle_store = MagicMock()
        # Create a simple Store message.
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Check it results in a call to the node's handle_store method.
        self.node.handle_store.assert_called_once_with(msg, self.protocol,
                                                       contact)

    def test_message_received_find_node(self):
        """
        Ensures a FindNode message is handled correctly.
        """
        self.node.handle_find_node = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        msg = FindNode(uuid, self.node_id, key, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_find_node method.
        self.node.handle_find_node.assert_called_once_with(msg, self.protocol)

    def test_message_received_find_value(self):
        """
        Ensures a FindValue message is handled correctly.
        """
        self.node.handle_find_value = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        msg = FindValue(uuid, self.node_id, key, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_find_value method.
        self.node.handle_find_value.assert_called_once_with(msg, self.protocol)

    def test_message_received_error(self):
        """
        Ensures an Error message is handled correctly.
        """
        self.node.handle_error = MagicMock()
        # Create an Error message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        code = 1
        title = ERRORS[code]
        details = {'foo': 'bar'}
        msg = Error(uuid, self.node_id, code, title, details, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Check it results in a call to the node's handle_error method.
        self.node.handle_error.assert_called_once_with(msg, self.protocol,
                                                       contact)

    def test_handle_ping(self):
        """
        Ensures the handle_ping method returns a Pong message.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
        # Check the result.
        result = Pong(uuid, self.node.id, version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_ping_loses_connection(self):
        """
        Ensures the handle_ping method loses the connection after sending the
        Pong.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_store(self):
        """
        Ensures a correct Store message is handled correctly.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Incoming message and peer
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        self.node.handle_store(msg, self.protocol, other_node)
        # Ensure the message is in local storage.
        self.assertIn(self.key, self.node._data_store)
        # Ensure the response is a Pong message.
        result = Pong(self.uuid, self.node.id, self.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_store_bad_message(self):
        """
        Ensures an invalid Store message is handled correctly.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Incoming message and peer
        msg = Store(self.uuid, self.node.id, self.key, 'wrong value',
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact('12345678abc', '127.0.0.1', 1908,
                             self.version, time.time())
        self.node._routing_table.add_contact(other_node)
        # Sanity check for expected routing table start state.
        self.assertEqual(1, len(self.node._routing_table._buckets[0]))
        # Handle faulty message.
        self.node.handle_store(msg, self.protocol, other_node)
        # Ensure the message is not in local storage.
        self.assertNotIn(self.key, self.node._data_store)
        # Ensure the contact is not in the routing table
        self.assertEqual(0, len(self.node._routing_table._buckets[0]))
        # Ensure the response is an Error message.
        details = {
            'message': 'You have been removed from remote routing table.'
        }
        result = Error(self.uuid, self.node.id, 6, ERRORS[6], details,
                       self.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_store_loses_connection(self):
        """
        Ensures the handle_store method with a good Store message loses the
        connection after sending the Pong message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Incoming message and peer
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        self.node.handle_store(msg, self.protocol, other_node)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_store_loses_connection_bad_message(self):
        """
        Ensures the handle_store method with an invalid message loses the
        connection after sending the Error message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Incoming message and peer
        msg = Store(self.uuid, self.node.id, self.key, 'wrong value',
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact('12345678abc', '127.0.0.1', 1908,
                             self.version, time.time())
        # Handle faulty message.
        self.node.handle_store(msg, self.protocol, other_node)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_find_nodes(self):
        """
        Ensure a valid FindNodes message is handled correctly.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Populate the routing table with contacts.
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            self.node._routing_table.add_contact(contact)
        # Incoming FindNode message
        msg = FindNode(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_node(msg, self.protocol)
        # Check the response sent back
        other_nodes = [(n.id, n.address, n.port, n.version) for n in
                       self.node._routing_table.find_close_nodes(self.key)]
        result = Nodes(msg.uuid, self.node.id, other_nodes, self.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_find_nodes_loses_connection(self):
        """
        Ensures the handle_find_nodes method loses the connection after
        sending the Nodes message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Populate the routing table with contacts.
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            self.node._routing_table.add_contact(contact)
        # Incoming FindNode message
        msg = FindNode(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_node(msg, self.protocol)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_find_value_with_match(self):
        """
        Ensures the handle_find_value method responds with a matching Value
        message if the value exists in the datastore.
        """
        # Store value.
        val = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        self.node._data_store.set_item(val.key, val)
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Check the response sent back
        result = Value(msg.uuid, self.node.id, val.key, val.value,
                       val.timestamp, val.expires, val.public_key, val.name,
                       val.meta, val.sig, val.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_find_value_no_match(self):
        """
        Ensures the handle_find_value method calls the handle_find_nodes
        method with the correct values if no matching value exists in the
        local datastore.
        """
        # Mock
        self.node.handle_find_node = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Check the response sent back
        self.node.handle_find_node.assert_called_once_with(msg, self.protocol)

    def test_handle_find_value_loses_connection(self):
        """
        Ensures the handle_find_value method loses the connection after
        sending the a matched value.
        """
        # Store value.
        val = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        self.node._data_store.set_item(val.key, val)
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_error_writes_to_log(self):
        """
        Ensures the handle_error method writes details about the error to the
        log.
        """
        log.msg = MagicMock()
        # Create an Error message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        code = 1
        title = ERRORS[code]
        details = {'foo': 'bar'}
        msg = Error(uuid, self.node_id, code, title, details, version)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Receive it...
        self.node.handle_error(msg, self.protocol, contact)
        # Check it results in two calls to the log.msg method (one to signify
        # an error has happened, the other the actual error message).
        self.assertEqual(2, log.msg.call_count)
