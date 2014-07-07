# -*- coding: utf-8 -*-
"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.version import get_version
from drogulus.dht.node import Node
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.storage import DictDataStore
from drogulus.dht.messages import from_dict
from drogulus.dht.crypto import get_signed_item, get_seal
from drogulus.dht.errors import BadMessage
from .keys import PRIVATE_KEY, PUBLIC_KEY
from mock import MagicMock, patch
from hashlib import sha512
import asyncio
import uuid
import unittest


class TestNode(unittest.TestCase):
    """
    Ensures the Node class works as expected.
    """

    def setUp(self):
        """
        Following the pattern explained here:
        """
        self.event_loop = asyncio.get_event_loop()
        self.version = get_version()
        self.uuid = str(uuid.uuid4())
        self.sender = PUBLIC_KEY
        self.recipient = PUBLIC_KEY
        self.reply_port = 1908
        self.version = get_version()
        self.value = 'a value'
        self.name = 'human readable key name'
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 9999)
        self.timestamp = signed_item['timestamp']
        self.key = signed_item['key']
        self.expires = signed_item['expires']
        self.created_with = signed_item['created_with']
        self.public_key = signed_item['public_key']
        self.signature = signed_item['signature']
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        self.seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = self.seal
        signed_item['message'] = 'value'
        self.signed_item = signed_item
        self.message = from_dict(signed_item)

    def test_init(self):
        """
        Ensures the class is instantiated correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop)
        self.assertEqual(node.public_key, PUBLIC_KEY)
        self.assertEqual(node.private_key, PRIVATE_KEY)
        self.assertEqual(node.event_loop, self.event_loop)
        expected_network_id = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        self.assertEqual(node.network_id, expected_network_id)
        self.assertIsInstance(node.routing_table, RoutingTable)
        self.assertEqual(node.routing_table._parent_node_id,
                         expected_network_id)
        self.assertIsInstance(node.data_store, DictDataStore)
        self.assertEqual(node.pending, {})
        self.assertEqual(node.version, self.version)

    def test_join(self):
        """
        Ensures the join method works with a valid set of seed_nodes.
        """
        # TODO implement this.
        pass

    def test_join_no_seed_nodes(self):
        """
        Ensure the correct exception is raised if the seed_nodes don't exist.
        """
        # TODO implement this.
        pass

    def test_message_received_checks_message_seal(self):
        """
        Ensure that the message_received method checks the message seal.
        """
        patcher = patch('drogulus.dht.node.check_seal')
        mock_check_seal = patcher.start()
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop)
        node.handle_value = MagicMock()
        node.message_received(self.message, 'http', '192.168.0.1', 1908)
        mock_check_seal.assert_called_once_with(self.message)
        patcher.stop()

    def test_message_received_bad_message_raises_exception(self):
        """
        Ensure that if an invalid message is received then a BadMessage
        exception is raised.
        """
        self.signed_item['seal'] = 'a bad seal'
        message = from_dict(self.signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop)
        self.assertRaises(BadMessage, node.message_received, message,
                          'http', '192.168.0.1', 1908)

    def test_message_received_processes_remote_contact(self):
        """
        Make sure that for *every* message reveived the associated contact
        at the other end is processed for potential inclusion in the routing
        table.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop)
        node.routing_table.add_contact = MagicMock()
        node.handle_value = MagicMock()
        node.message_received(self.message, 'http', '192.168.0.1', 1908)
        uri = 'http://192.168.0.1:1908'
        self.assertEqual(1, node.routing_table.add_contact.call_count)
        argument = node.routing_table.add_contact.call_args_list[0][0][0]
        self.assertEqual(argument.public_key, self.message.sender)
        self.assertEqual(argument.version, self.message.version)
        self.assertEqual(argument.uri, uri)
        self.assertIsInstance(argument.last_seen, float)

    def test_message_received_ping(self):
        """
        Make sure a Ping message is handled correctly with a return Pong.
        """
        assert False

    def test_message_received_pong(self):
        """
        Make sure a Pong message is handled correctly by resolving the
        correct pending Future.
        """
        assert False

    def test_message_received_store(self):
        """
        Ensure a Store message results in the data being checked and data
        being stored.
        """
        assert False

    def test_message_received_find_node(self):
        """
        Make sure a FindNode message returns a Nodes response.
        """
        assert False

    def test_message_received_find_value(self):
        """
        Make sure a FindValue message returns something appropriate like a
        Value message.
        """
        assert False

    def test_message_received_error(self):
        """
        Make sure error messages are handled correctly.
        """
        assert False

    def test_message_received_value(self):
        """
        Ensure a Value message results in the data being checked and the
        correct Future being resolved with the expected result.
        """
        assert False

    def test_message_received_nodes(self):
        """
        Ensure a Nodes message results in the list of peer nodes being
        checked and the correct Future being resolved with the expected
        result.
        """
        assert False
