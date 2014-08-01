# -*- coding: utf-8 -*-
"""
Tests for the core Drogulus class
"""
from drogulus.node import Drogulus
from drogulus.dht.node import Node
from .dht.keys import PUBLIC_KEY, PRIVATE_KEY
import unittest
import asyncio


class TestDrogulus(unittest.TestCase):
    """
    Ensures the core Drogulus class works as expected.
    """

    def test_init(self):
        """
        Ensure the Drogulus instance is created as expected.
        """
        event_loop = asyncio.get_event_loop()
        d = Drogulus(PRIVATE_KEY, PUBLIC_KEY, event_loop)
        self.assertEqual(d.private_key, PRIVATE_KEY)
        self.assertEqual(d.public_key, PUBLIC_KEY)
        self.assertEqual(d.event_loop, event_loop)
        self.assertEqual(d.alias, {})
        self.assertIsInstance(d._node, Node)
