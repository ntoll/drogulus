"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import Node
from drogulus.dht.constants import ERRORS
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus.dht.net import DHTFactory
from drogulus.dht.messages import Ping, Pong
from twisted.trial import unittest
from twisted.test import proto_helpers
from mock import MagicMock
from uuid import uuid4
import hashlib
import time
import re


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

    def test_init(self):
        """
        Ensures the class is instantiated correctly.
        """
        node = Node(123)
        self.assertEqual(123, node.id)
        self.assertTrue(node._routing_table)
        self.assertTrue(node._data_store)
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
        self.protocol.sendMessage = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
        # Check the result.
        result = Pong(uuid, self.node.id, version)
        self.protocol.sendMessage.assert_called_once_with(result)
