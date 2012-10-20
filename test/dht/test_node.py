"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import Node
import unittest

class TestNode(unittest.TestCase):
    """
    Ensures the Node class works as expected.
    """

    def testInit(self):
        """
        Ensures the class is instantiated correctly.
        """
        node = Node(123)
        self.assertEqual(123, node.id)
        self.assertTrue(node._routing_table)
        self.assertTrue(node._data_store)
