# -*- coding: utf-8 -*-
"""
Tests for the core Drogulus class
"""
from drogulus.version import get_version
from drogulus.node import Drogulus
from drogulus.dht.node import Node
from drogulus.dht.crypto import construct_key
from drogulus.dht.constants import DUPLICATION_COUNT
from drogulus.net.netstring import NetstringConnector
from .dht.keys import PUBLIC_KEY, BAD_PUBLIC_KEY, PRIVATE_KEY
from unittest.mock import MagicMock
import unittest
import json
import asyncio


class TestDrogulus(unittest.TestCase):
    """
    Ensures the core Drogulus class works as expected.
    """

    def setUp(self):
        """
        A whole bunch of generic stuff we regularly need to faff about with
        that are set to some sane defaults.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        self.connector = NetstringConnector(self.event_loop)
        self.version = get_version()

    def tearDown(self):
        """
        Clean up the event loop.
        """
        self.event_loop.close()

    def test_init(self):
        """
        Ensure the Drogulus instance is created as expected.
        """
        d = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop, self.connector)
        self.assertEqual(d.private_key, PRIVATE_KEY)
        self.assertEqual(d.public_key, PUBLIC_KEY)
        self.assertEqual(d.event_loop, self.event_loop)
        self.assertEqual(d.connector, self.connector)
        self.assertIsInstance(d._node, Node)
        self.assertEqual(d._node.reply_port, 1908)
        self.assertEqual(d.whoami['public_key'], PUBLIC_KEY)
        self.assertEqual(d.whoami['version'], get_version())

    def test_init_bespoke_port(self):
        """
        Ensure the Drogulus instance passes on the port information to its
        Node instance.
        """
        d = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop, self.connector,
                     port=9999)
        self.assertEqual(d._node.reply_port, 9999)

    def test_init_with_whoami_dict(self):
        """
        Ensure that arbitrary data passed in as the whoami argument ends up
        set in the node's whoami attribute.
        """
        whoami = {
            'name': 'fred'
        }
        d = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop, self.connector,
                     whoami=whoami)
        self.assertEqual(d.whoami['public_key'], PUBLIC_KEY)
        self.assertEqual(d.whoami['version'], get_version())
        self.assertEqual(d.whoami['name'], 'fred')

    def test_join_with_peers(self):
        """
        Ensure that the join method works as expected given a valid list of
        existing contacts on the network.
        """
        version = get_version()
        data_dump = {
            'contacts': [
                {
                    'public_key': PUBLIC_KEY,
                    'version': version,
                    'uri': 'http://192.168.0.1:1908',
                },
            ],
            'blacklist': [BAD_PUBLIC_KEY, ]
        }
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = asyncio.Future()
        drog._node.join = MagicMock(return_value=result)
        drog.join(data_dump)
        drog._node.join.assert_called_once_with(data_dump)
        drog.set = MagicMock()
        result.set_result(True)
        self.event_loop.run_until_complete(result)
        drog.set.assert_called_once_with(drog.whoami['public_key'],
                                         drog.whoami)

    def test_join_no_peers(self):
        """
        Ensure a ValueError is raised if an empty list of contacts is passed
        into the join method.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        with self.assertRaises(ValueError):
            drog.join({})

    def test_dump_routing_table(self):
        """
        Ensure the routing table is dumped into a data structure that can be
        serialised into JSON.
        """
        version = get_version()
        data_dump = {
            'contacts': [
                {
                    'public_key': PUBLIC_KEY,
                    'version': version,
                    'uri': 'http://192.168.0.1:1908',
                },
            ],
            'blacklist': [BAD_PUBLIC_KEY, ]
        }
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        drog._node.routing_table.restore(data_dump)
        result = drog.dump_routing_table()
        self.assertIsInstance(result, dict)
        self.assertIn('contacts', result)
        self.assertIn('blacklist', result)
        serialised = json.dumps(result)
        self.assertIsInstance(serialised, str)

    def test_whois(self):
        """
        Check that the whois method makes the appropriate request to the
        wider network.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = asyncio.Future()
        drog.get = MagicMock(return_value=result)
        pending_result = drog.whois(PUBLIC_KEY)
        drog.get.assert_called_once_with(PUBLIC_KEY, PUBLIC_KEY)
        self.assertEqual(result, pending_result)

    def test_get(self):
        """
        Ensure that the node's get method works as expected.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = asyncio.Future()
        drog._node.retrieve = MagicMock(return_value=result)
        pending_result = drog.get(PUBLIC_KEY, 'foo')
        expected = construct_key(PUBLIC_KEY, 'foo')
        drog._node.retrieve.assert_called_once_with(expected)
        self.assertEqual(result, pending_result)

    def test_set(self):
        """
        Ensure a basic set operation works as expected.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = []
        for i in range(20):
            result.append(asyncio.Future())
        drog._node.replicate = MagicMock(return_value=result)
        pending_result = drog.set('foo', 'bar')
        self.assertIsInstance(pending_result, list)
        self.assertEqual(1, drog._node.replicate.call_count)
        called_with = drog._node.replicate.call_args_list[0][0]
        self.assertEqual(called_with[0], DUPLICATION_COUNT)
        self.assertEqual(called_with[1], construct_key(PUBLIC_KEY, 'foo'))
        self.assertEqual(called_with[2], 'bar')
        self.assertIsInstance(called_with[3], float)
        self.assertEqual(called_with[4], 0.0)
        self.assertEqual(called_with[5], self.version)
        self.assertEqual(called_with[6], PUBLIC_KEY)
        self.assertEqual(called_with[7], 'foo')
        self.assertIsInstance(called_with[8], str)

    def test_set_with_expiry(self):
        """
        Ensure the expiry setting is passed into the replicate method.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = []
        for i in range(20):
            result.append(asyncio.Future())
        drog._node.replicate = MagicMock(return_value=result)
        pending_result = drog.set('foo', 'bar', expires=99999)
        self.assertIsInstance(pending_result, list)
        self.assertEqual(1, drog._node.replicate.call_count)
        called_with = drog._node.replicate.call_args_list[0][0]
        self.assertEqual(called_with[0], DUPLICATION_COUNT)
        self.assertEqual(called_with[1], construct_key(PUBLIC_KEY, 'foo'))
        self.assertEqual(called_with[2], 'bar')
        self.assertIsInstance(called_with[3], float)
        self.assertEqual(called_with[4], called_with[3] + 99999)
        self.assertEqual(called_with[5], self.version)
        self.assertEqual(called_with[6], PUBLIC_KEY)
        self.assertEqual(called_with[7], 'foo')
        self.assertIsInstance(called_with[8], str)

    def test_set_bespoke_duplication_count(self):
        """
        Ensure the duplication count is passed into the replicate method.
        """
        drog = Drogulus(PRIVATE_KEY, PUBLIC_KEY, self.event_loop,
                        self.connector)
        result = []
        for i in range(20):
            result.append(asyncio.Future())
        drog._node.replicate = MagicMock(return_value=result)
        pending_result = drog.set('foo', 'bar', duplicate=5)
        self.assertIsInstance(pending_result, list)
        self.assertEqual(1, drog._node.replicate.call_count)
        called_with = drog._node.replicate.call_args_list[0][0]
        self.assertEqual(called_with[0], 5)
        self.assertEqual(called_with[1], construct_key(PUBLIC_KEY, 'foo'))
        self.assertEqual(called_with[2], 'bar')
        self.assertIsInstance(called_with[3], float)
        self.assertEqual(called_with[4], 0.0)
        self.assertEqual(called_with[5], self.version)
        self.assertEqual(called_with[6], PUBLIC_KEY)
        self.assertEqual(called_with[7], 'foo')
        self.assertIsInstance(called_with[8], str)
