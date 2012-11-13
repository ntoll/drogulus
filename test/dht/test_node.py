"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import Node
from drogulus.version import get_version
from drogulus.dht.net import DHTFactory
from drogulus.dht.messages import Ping, Pong
from twisted.trial import unittest
from twisted.test import proto_helpers
from mock import MagicMock
from uuid import uuid4
import hashlib
import time


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

    def test_message_received_ping(self):
        """
        Ensures a Ping message is handled correctly.
        """
        self.node.handle_ping = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's message_received method.
        self.node.handle_ping.assert_called_once_with(msg, self.protocol)

    def test_handle_ping(self):
        """
        Ensures the handle_ping method returns a Pong message.
        """
        self.protocol.transport.sendMessage = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
        # Check the result.
        result = Pong(uuid, version)
        self.protocol.transport.sendMessage.assert_called_once_with(result)
