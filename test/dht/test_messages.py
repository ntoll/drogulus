"""
A set of sanity checks to ensure that the messages are defined as expected.
"""
from drogulus.dht.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
    FindValue, Value)
import unittest

class TestMessages(unittest.TestCase):
    """
    Ensures the message classes are *defined* as expected and the relevant
    fields can be indexed.
    """

    def test_error(self):
        """
        Expected behaviour of an error message.
        """
        error = Error(1, 2, 'This is an error', {'foo': 'bar'}, 0.1)
        self.assertEqual(1, error.id)
        self.assertEqual(2, error.code)
        self.assertEqual('This is an error', error.title)
        self.assertEqual({'foo': 'bar'}, error.details)
        self.assertEqual(0.1, error.version)

    def test_ping(self):
        """
        Expected behaviour of a ping message.
        """
        ping = Ping(1, 0.1)
        self.assertEqual(1, ping.id)
        self.assertEqual(0.1, ping.version)

    def test_pong(self):
        """
        Expected behaviour of a pong message.
        """
        pong = Pong(1, 0.1)
        self.assertEqual(1, pong.id)
        self.assertEqual(0.1, pong.version)

    def test_store(self):
        """
        Expected behaviour of a store message.
        """
        store = Store(1, 2, 'value', 12345, 'abcdefg', 'name', 'meta', 'hash',
            0.1)
        self.assertEqual(1, store.id)
        self.assertEqual(2, store.key)
        self.assertEqual('value', store.value)
        self.assertEqual(12345, store.time)
        self.assertEqual('abcdefg', store.public_key)
        self.assertEqual('name', store.name)
        self.assertEqual('hash', store.hash)
        self.assertEqual(0.1, store.version)

    def test_find_node(self):
        """
        Expected behaviour of a findnode message.
        """
        fn = FindNode(1, 'key', 0.1)
        self.assertEqual(1, fn.id)
        self.assertEqual('key', fn.key)
        self.assertEqual(0.1, fn.version)

    def test_nodes(self):
        """
        Expected behaviour of a nodes message.
        """
        nodes = Nodes(1, [('127.0.0.1', 1908)], 0.1)
        self.assertEqual(1, nodes.id)
        self.assertEqual([('127.0.0.1', 1908)], nodes.nodes)
        self.assertEqual(0.1, nodes.version)

    def test_find_value(self):
        """
        Expected behaviour of a findvalue message.
        """
        fv = FindValue(1, 'key', 0.1)
        self.assertEqual(1, fv.id)
        self.assertEqual('key', fv.key)
        self.assertEqual(0.1, fv.version)

    def test_value(self):
        """
        Expected behaviour of a value message.
        """
        val = Value(1, 2, 'value', 12345, 'abcdefg', 'name', 'meta', 'hash',
            0.1)
        self.assertEqual(1, val.id)
        self.assertEqual(2, val.key)
        self.assertEqual('value', val.value)
        self.assertEqual(12345, val.time)
        self.assertEqual('abcdefg', val.public_key)
        self.assertEqual('name', val.name)
        self.assertEqual('hash', val.hash)
        self.assertEqual(0.1, val.version)
