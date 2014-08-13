# -*- coding: utf-8 -*-
"""
A rather silly test but added all the same for completeness and to check the
initial test suite works as expected.
"""
from drogulus.net.connector import Connector
import unittest
import asyncio


class TestConnector(unittest.TestCase):
    """
    Ensures the drogulus.net.connector.Connector class is defined as expected.
    """

    def test_init(self):
        """
        Check the passed in event loop is added to the connector object.
        """
        loop = asyncio.get_event_loop()
        c = Connector(loop)
        self.assertEqual(c.event_loop, loop)

    def test_send(self):
        """
        Ensures the send method raises a NotImplemented exception.
        """
        loop = asyncio.get_event_loop()
        c = Connector(loop)
        with self.assertRaises(NotImplementedError):
            c.send('foo', 'bar')

    def test_receive(self):
        """
        Ensures the receive method raises a NotImplemented exception.
        """
        loop = asyncio.get_event_loop()
        c = Connector(loop)
        with self.assertRaises(NotImplementedError):
            c.receive('foo', 'bar', 'baz', 'qux')
