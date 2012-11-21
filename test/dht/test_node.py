"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import Node
from drogulus.dht.constants import ERRORS
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus.dht.net import DHTFactory
from drogulus.dht.messages import Error, Ping, Pong, Store
from drogulus.dht.crypto import construct_key
from twisted.trial import unittest
from twisted.test import proto_helpers
from mock import MagicMock
from uuid import uuid4
import hashlib
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
        hasher = hashlib.sha1()
        hasher.update(str(time.time()))
        self.node_id = hasher.hexdigest()
        self.node = Node(self.node_id)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)
        self.signature = ('\xadqPs\xcf@\x01r\xe4\xc5^?\x0e\x89o\xfc-\xe1?{%' +
                          '\x9a\x8f\x8f\xb9\xa4\xc2\x96\xf9b\xeb?\xa8\xdbL' +
                          '\xeb\xa1\xec9\xe6q\xad2\xd9\xfb\xa2t+\xb9\xf8' +
                          '\xb6r/|\x87\xb9\xd8\x88_D\xff\xd9\x1a\x7fV<P/\rL' +
                          '\xd1Z\xb2\x10\xc5\xa5\x1e\xf2\xdaqP{\x9e\xa6[{' +
                          '\xc5\x849\xc6\x92\x0f\xe5\x88\x05\x92\x82' +
                          '\x15[y\\_b8V\x8c\xab\x82B\xcd\xaey\xcc\x980p\x0e5' +
                          '\xcf\xf4\xa7?\x94\x8a\\Z\xc4\x8a')
        self.value = 'value'
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
        # Check it results in a call to the node's message_received method.
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
        # Check it results in a call to the node's message_received method.
        self.node.handle_ping.assert_called_once_with(msg, self.protocol)

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
        Ensures the handle_ping method returns a Pong message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
        # Check the result.
        Pong(uuid, self.node.id, version)
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
