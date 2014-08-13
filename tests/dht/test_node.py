# -*- coding: utf-8 -*-
"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.version import get_version
from drogulus.dht.node import Node
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.storage import DictDataStore
from drogulus.dht.messages import (Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value, from_dict, to_dict)
from drogulus.dht.crypto import (get_signed_item, get_seal, check_seal,
                                 construct_key, _get_hash, PKCS1_v1_5, RSA,
                                 verify_item)
from drogulus.dht.errors import (BadMessage, UnverifiableProvenance, TimedOut,
                                 RoutingTableEmpty)
from drogulus.dht.contact import PeerNode
from drogulus.dht.constants import (REPLICATE_INTERVAL, REFRESH_INTERVAL,
                                    RESPONSE_TIMEOUT)
from drogulus.dht.bucket import Bucket
from .keys import PRIVATE_KEY, PUBLIC_KEY, BAD_PUBLIC_KEY
from mock import MagicMock, patch
from hashlib import sha512
import asyncio
import uuid
import base64
import time
import unittest
import mock


@asyncio.coroutine
def blip():
    """
    A coroutine that immediately return to allow tasks scheduled in the tests
    to run.

    THIS IS A QUICK HACK AND SHOULD BE CHANGED TO SOMETHING MORE ELEGANT.
    """
    return True


class FakeConnector:
    """
    Pretends to be a connector for sending messages to remote nodes. A
    connector instance abstracts the node from the underlying network protocol
    for sending messages.
    """

    def __init__(self):
        self.messages = []

    def send(self, contact, message):
        """
        Pretends to send a message to the specified contact.
        """
        self.future = asyncio.Future()
        self.messages.append((contact, message))
        return self.future


class TestNode(unittest.TestCase):
    """
    Ensures the Node class works as expected.
    """

    def setUp(self):
        """
        A whole bunch of generic stuff we regularly need to faff about with
        that are set to some sane defaults.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        self.connector = FakeConnector()
        self.version = get_version()
        self.uuid = str(uuid.uuid4())
        self.sender = PUBLIC_KEY
        self.recipient = PUBLIC_KEY
        self.reply_port = 1908
        self.version = get_version()
        self.value = 'a value'
        self.name = 'human readable key name'
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 999999)
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
        self.contact = PeerNode(PUBLIC_KEY, self.version,
                                'http://192.168.0.1:1908')

    def tearDown(self):
        """
        Clean up the event loop.
        """
        self.event_loop.close()

    def test_init(self):
        """
        Ensures the class is instantiated correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
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
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        seed_nodes = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            seed_nodes.append(contact)
        node.routing_table.add_contact = mock.MagicMock()
        lookup_patcher = patch('drogulus.dht.node.Lookup')
        mock_lookup = lookup_patcher.start()
        with patch.object(self.event_loop, 'call_later') as mock_call:
            node.join(seed_nodes)
            mock_call.assert_called_once_with(REFRESH_INTERVAL, node.refresh)
        mock_lookup.assert_called_once_with(FindNode, node.network_id, node,
                                            node.event_loop)
        lookup_patcher.stop()
        self.assertEqual(len(seed_nodes),
                         node.routing_table.add_contact.call_count)

    def test_join_no_seed_nodes(self):
        """
        Ensure the correct exception is raised if the seed_nodes don't exist.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        with self.assertRaises(ValueError):
            node.join([])

    def test_message_received_checks_message_seal(self):
        """
        Ensure that the message_received method checks the message seal.
        """
        patcher = patch('drogulus.dht.node.check_seal')
        mock_check_seal = patcher.start()
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
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
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        self.assertRaises(BadMessage, node.message_received, message,
                          'http', '192.168.0.1', 1908)

    def test_message_received_processes_remote_contact(self):
        """
        Make sure that for *every* message reveived the associated contact
        at the other end is processed for potential inclusion in the routing
        table.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
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
        Make sure a Ping message is handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_ping = mock.MagicMock()
        ping = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(ping, PRIVATE_KEY)
        ping['seal'] = seal
        ping['message'] = 'ping'
        message = from_dict(ping)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_ping.assert_called_once_with(message, self.contact)

    def test_handle_ping(self):
        """
        Ensure that the handle_ping method returns a pong.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        ping = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(ping, PRIVATE_KEY)
        ping['seal'] = seal
        ping['message'] = 'ping'
        message = from_dict(ping)
        node.handle_ping(message, self.contact)
        self.event_loop.run_until_complete(blip())
        self.assertEqual(1, len(self.connector.messages))
        contact = self.connector.messages[0][0]
        sent = self.connector.messages[0][1]
        # Contact is good from data in ping message.
        self.assertEqual(contact.public_key, PUBLIC_KEY)
        self.assertEqual(contact.uri, 'http://192.168.0.1:1908')
        self.assertEqual(contact.version, message.version)
        self.assertEqual(contact.failed_RPCs, 0)
        self.assertIsInstance(contact.last_seen, float)
        expected = sha512(contact.public_key.encode('utf-8')).hexdigest()
        self.assertEqual(contact.network_id, expected)
        # Pong message is correct.
        self.assertEqual(sent.uuid, message.uuid)
        self.assertEqual(sent.recipient, PUBLIC_KEY)
        self.assertEqual(sent.sender, PUBLIC_KEY)
        self.assertEqual(sent.version, self.version)
        self.assertEqual(sent.reply_port, 1908)
        self.assertTrue(check_seal(sent))
        self.assertIsInstance(sent, Pong)

    def test_message_received_pong(self):
        """
        Make sure a Pong message is handled correctly by resolving the
        correct pending Future.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_pong = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'pong'
        message = from_dict(msg_dict)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_pong.assert_called_once_with(message)

    def test_handle_pong(self):
        """
        Make sure a Pong message is handled correctly by resolving the
        correct pending Future.
        """
        # Make a source ping message.
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'ping'
        message = from_dict(msg_dict)
        node.send_message(self.contact, message)
        self.event_loop.run_until_complete(blip())
        # Check the task is in the node's pending dictionary.
        self.assertIn(message.uuid, node.pending)
        self.assertIsInstance(node.pending[message.uuid], asyncio.Future)
        task = node.pending[message.uuid]
        # Receive the Ping response
        msg_dict['message'] = 'pong'
        reply = from_dict(msg_dict)
        node.message_received(reply, 'http', '192.168.0.1', 1908)
        self.event_loop.run_until_complete(blip())
        # Check the task is no longer in the node's pending dictionary and has
        # been resolved with the Pong message.
        self.assertNotIn(message.uuid, node.pending)
        self.assertEqual(True, task.done())
        self.assertEqual(reply, task.result())
        # Make a source ping message.
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'ping'
        message = from_dict(msg_dict)
        node.send_message(self.contact, message)
        self.event_loop.run_until_complete(blip())
        # Check the task is in the node's pending dictionary.
        self.assertIn(message.uuid, node.pending)
        self.assertIsInstance(node.pending[message.uuid], asyncio.Future)
        task = node.pending[message.uuid]
        # Receive the Pong response
        msg_dict['message'] = 'pong'
        reply = from_dict(msg_dict)
        node.handle_pong(reply)
        self.event_loop.run_until_complete(blip())
        # Check the task is no longer in the node's pending dictionary and has
        # been resolved with the Pong message.
        self.assertNotIn(message.uuid, node.pending)
        self.assertEqual(True, task.done())
        self.assertEqual(reply, task.result())

    def test_message_received_store(self):
        """
        Ensure a Store message is handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_store = mock.MagicMock()
        self.signed_item['message'] = 'store'
        message = from_dict(self.signed_item)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_store.assert_called_once_with(message, self.contact)

    def test_handle_store(self):
        """
        Ensure a Store message results in the data being checked, data
        being stored, a pong being returned to the remote peer and a
        republish command being scheduled in the future.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_pong = mock.MagicMock()
        self.signed_item['message'] = 'store'
        message = from_dict(self.signed_item)
        with patch.object(self.event_loop, 'call_later') as mock_call:
            node.handle_store(message, self.contact)
            self.assertEqual(1, mock_call.call_count)
            self.assertEqual(mock_call.call_args_list[0][0][0],
                             REPLICATE_INTERVAL)
            self.assertEqual(mock_call.call_args_list[0][0][1],
                             node.republish)
            self.assertEqual(mock_call.call_args_list[0][0][2],
                             message.key)
        self.assertEqual(message, node.data_store[message.key])
        self.assertEqual(1, node.send_pong.call_count)
        node.send_pong.assert_called_once_with(message, self.contact)

    def test_handle_store_bad_signature(self):
        """
        Ensure a Store message that isn't signed correctly is rejected and the
        sending node is blacklisted.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.routing_table.blacklist = mock.MagicMock()
        self.signed_item['message'] = 'store'
        self.signed_item['signature'] = 'thiswillfail'
        message = from_dict(self.signed_item)
        with self.assertRaises(UnverifiableProvenance):
            node.handle_store(message, self.contact)
            node.routing_table.blacklist.assert_called_once_with(self.contact)

    def test_handle_store_key_mismatch(self):
        """
        If a Store message is attempting to store a value at a key that
        doesn't derive from the public key and name associated with the value
        then raise an error.

        THIS MISMATCH SHOULD NEVER HAPPEN - but if it does, it mustn't be
        allowed to propagate around the network. Ergo the need to take steps
        to mitigate such an event.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        signed_item = {
            'name': self.key,
            'value': self.value,
            'created_with': get_version(),
            'public_key': PUBLIC_KEY,
            'timestamp': time.time(),
            'key': construct_key(BAD_PUBLIC_KEY, 'Incorrect key/hash.'),
            'expires': 0.0,
        }
        root_hash = _get_hash(signed_item)
        key = RSA.importKey(PRIVATE_KEY)
        signer = PKCS1_v1_5.new(key)
        sig = base64.encodebytes(signer.sign(root_hash)).decode('utf-8')
        signed_item['signature'] = sig
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        self.seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = self.seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        with self.assertRaises(BadMessage) as ex:
            node.handle_store(message, self.contact)
        self.assertEqual('Key mismatch', ex.exception.args[0])

    def test_handle_store_expired(self):
        """
        If a Store message is attempting to store an expired value then
        raise an error.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0.000001)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        self.seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = self.seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        with self.assertRaises(BadMessage) as ex:
            node.handle_store(message, self.contact)
        self.assertIn('Expired at ', ex.exception.args[0])
        self.assertIn('current time: ', ex.exception.args[0])

    def test_handle_store_out_of_date(self):
        """
        If a Store message is attempting to store a superseded value then
        raise an error.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        old_signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                          PRIVATE_KEY)
        old_signed_item['uuid'] = self.uuid
        old_signed_item['sender'] = self.sender
        old_signed_item['recipient'] = self.recipient
        old_signed_item['reply_port'] = self.reply_port
        old_signed_item['version'] = self.version
        self.seal = get_seal(old_signed_item, PRIVATE_KEY)
        old_signed_item['seal'] = self.seal
        old_signed_item['message'] = 'store'
        older_message = from_dict(old_signed_item)
        new_signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                          PRIVATE_KEY, 999999)
        new_signed_item['uuid'] = self.uuid
        new_signed_item['sender'] = self.sender
        new_signed_item['recipient'] = self.recipient
        new_signed_item['reply_port'] = self.reply_port
        new_signed_item['version'] = self.version
        self.seal = get_seal(new_signed_item, PRIVATE_KEY)
        new_signed_item['seal'] = self.seal
        new_signed_item['message'] = 'store'
        newer_message = from_dict(new_signed_item)
        node.handle_store(newer_message, self.contact)
        # Try to store the older message.
        with self.assertRaises(BadMessage) as ex:
            node.handle_store(older_message, self.contact)
        self.assertIn('Out of date. New timestamp: ', ex.exception.args[0])

    def test_message_received_find_node(self):
        """
        Make sure a FindNode message is handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_find_node = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'key': sha512('a key'.encode('utf-8')).hexdigest(),
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'findnode'
        message = from_dict(msg_dict)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_find_node.assert_called_once_with(message, self.contact)

    def test_handle_find_node(self):
        """
        Make sure a FindNode message returns a Nodes response.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_nodes = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'key': sha512('a key'.encode('utf-8')).hexdigest(),
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'findnode'
        message = from_dict(msg_dict)
        node.handle_find_node(message, self.contact)
        self.assertEqual(1, node.send_nodes.call_count)
        m, c, n = node.send_nodes.call_args_list[0][0]
        self.assertEqual(m, message)
        self.assertEqual(c, self.contact)
        self.assertIsInstance(n, list)

    def test_message_received_find_value(self):
        """
        Make sure a FindValue message is handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_find_value = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'key': sha512('a key'.encode('utf-8')).hexdigest(),
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'findvalue'
        message = from_dict(msg_dict)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_find_value.assert_called_once_with(message, self.contact)

    def test_handle_find_value_exists(self):
        """
        Make sure a FindValue message causes a Value message to be sent to the
        remote peer if the local node has the requested key/value item. Also
        check that the item is "touched" in the local data store to update its
        last-access timestamp.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        k = sha512('a key'.encode('utf-8')).hexdigest()
        node.data_store[k] = self.message
        node.send_value = mock.MagicMock()
        node.data_store.touch = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'key': k,
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'findvalue'
        message = from_dict(msg_dict)
        node.handle_find_value(message, self.contact)
        self.assertEqual(1, node.send_value.call_count)
        args = node.send_value.call_args_list[0][0]
        self.assertEqual(message, args[0])
        self.assertEqual(self.contact, args[1])
        self.assertEqual(self.message.key, args[2])
        self.assertEqual(self.message.value, args[3])
        self.assertEqual(self.message.timestamp, args[4])
        self.assertEqual(self.message.expires, args[5])
        self.assertEqual(self.message.created_with, args[6])
        self.assertEqual(self.message.public_key, args[7])
        self.assertEqual(self.message.name, args[8])
        self.assertEqual(self.message.signature, args[9])
        self.assertEqual(1, node.data_store.touch.call_count)
        node.data_store.touch.assert_called_once_with(k)

    def test_handle_find_value_unknown_key(self):
        """
        Make sure a FindValue message for an unknown key/value pair causes the
        same result as a call to handle_find_node.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        k = sha512('a key'.encode('utf-8')).hexdigest()
        node.handle_find_node = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'key': k,
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'findvalue'
        message = from_dict(msg_dict)
        node.handle_find_value(message, self.contact)
        node.handle_find_node.assert_called_once_with(message, self.contact)

    def test_message_received_error(self):
        """
        Make sure error messages are handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_error = mock.MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'error': 'ValueError',
            'details': 'Some arbitrary but useful text about the error',
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'error'
        message = from_dict(msg_dict)
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_error.assert_called_once_with(message, self.contact)

    def test_handle_error(self):
        """
        Makes sure remote errors are logged in the expected manner.
        """
        patcher = patch('drogulus.dht.node.logging.info')
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'error': 'ValueError',
            'details': 'Some arbitrary but useful text about the error',
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'error'
        message = from_dict(msg_dict)
        mock_log = patcher.start()
        node.handle_error(message, self.contact)
        self.assertEqual(2, mock_log.call_count)
        expected = '***** ERROR ***** from '
        self.assertTrue(mock_log.call_args_list[0][0][0].startswith(expected))
        self.assertEqual(mock_log.call_args_list[1][0][0], message)
        patcher.stop()

    def test_message_received_value(self):
        """
        Ensure that Value messages are handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.handle_value = mock.MagicMock()
        node.message_received(self.message, 'http', '192.168.0.1', 1908)
        node.handle_value.assert_called_once_with(self.message, self.contact)

    def test_handle_value_valid(self):
        """
        Ensure a Value message results in the data being checked and the
        correct Future being resolved with the expected result.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.trigger_task = mock.MagicMock()
        node.handle_value(self.message, self.contact)
        node.trigger_task.assert_called_once_with(self.message)

    def test_handle_value_not_valid(self):
        """
        Ensure an invalid Value message results in the correct Future being
        resolved with the expected exception. Furthermore, the remote peer is
        forcibly removed from the local node's routing table. Finally, such
        activity is appropriately logged.
        """
        patcher = patch('drogulus.dht.node.logging.info')
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.trigger_task = mock.MagicMock()
        node.routing_table.remove_contact = MagicMock()
        self.signed_item['public_key'] = BAD_PUBLIC_KEY
        message = from_dict(self.signed_item)
        mock_log = patcher.start()
        node.handle_value(message, self.contact)
        self.assertEqual(3, mock_log.call_count)
        node.routing_table.remove_contact.\
            assert_called_once_with(self.contact.network_id, True)
        self.assertEqual(1, node.trigger_task.call_count)
        m = node.trigger_task.call_args_list[0][0][0]
        e = node.trigger_task.call_args_list[0][1]['error']
        self.assertEqual(m, message)
        self.assertIsInstance(e, UnverifiableProvenance)
        self.assertEqual('Blacklisted', e.args[0])
        patcher.stop()

    def test_message_received_nodes(self):
        """
        Ensure a Nodes message is handled correctly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'nodes': ((PUBLIC_KEY, self.version, 'http://192.168.0.1:1908/'),)
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'nodes'
        message = from_dict(msg_dict)
        node.handle_nodes = mock.MagicMock()
        node.message_received(message, 'http', '192.168.0.1', 1908)
        node.handle_nodes.assert_called_once_with(message)

    def test_handle_nodes(self):
        """
        Ensure a Nodes message results in the list of peer nodes being
        checked and the correct Future being resolved with the expected
        result.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.trigger_task = MagicMock()
        msg_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': self.version,
            'nodes': ((PUBLIC_KEY, self.version, 'http://192.168.0.1:1908/'),)
        }
        seal = get_seal(msg_dict, PRIVATE_KEY)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'nodes'
        message = from_dict(msg_dict)
        node.handle_nodes(message)
        node.trigger_task.assert_called_once_with(message)

    def test_trigger_task(self):
        """
        Ensure the referenced task is resolved with the passed in message. The
        task must also be removed from the pending dict of the local node.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        pending_task = asyncio.Future()
        node.pending[self.message.uuid] = pending_task
        node.trigger_task(self.message)
        self.assertEqual(0, len(node.pending))
        self.assertTrue(pending_task.done())
        self.assertEqual(self.message, pending_task.result())

    def test_trigger_task_with_error(self):
        """
        Ensure the referenced task is resolved with referenced exception. The
        task must also be removed from the pending dict of the local node.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        pending_task = asyncio.Future()
        node.pending[self.message.uuid] = pending_task
        ex = UnverifiableProvenance('Blacklisted')
        node.trigger_task(self.message, error=ex)
        with self.assertRaises(UnverifiableProvenance):
            self.event_loop.run_until_complete(pending_task)
        self.assertEqual(0, len(node.pending))
        self.assertTrue(pending_task.done())
        self.assertEqual(ex, pending_task.exception())

    def test_trigger_task_for_resolved_future(self):
        """
        If the task/future has already been resolved then simply just remove
        it from the pending dictionary.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        pending_task = asyncio.Future()
        node.pending[self.message.uuid] = pending_task
        pending_task.set_result('done!')
        node.trigger_task(self.message)
        self.assertEqual(0, len(node.pending))

    def test_send_message(self):
        """
        Ensure that the send_message creates a task that is added to the
        local node's pending dict, adds an on_complete callback and returns
        the task as a result. Additionally, checks that a the task times out
        after RESPONSE_TIMEOUT seconds.

        When the task is resolved the on_complete callback should remove it
        from the local node's pending dict.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        with patch.object(self.event_loop, 'call_later') as mock_call:
            uuid, task = node.send_message(self.contact, self.message)
            self.connector.future.set_result('done')
            self.event_loop.run_until_complete(blip())
            self.assertEqual(1, mock_call.call_count)
            self.assertEqual(mock_call.call_args_list[0][0][0],
                             RESPONSE_TIMEOUT)
            self.assertEqual(mock_call.call_args_list[0][0][1],
                             node.trigger_task)
            self.assertEqual(mock_call.call_args_list[0][0][2],
                             self.message)
            self.assertIsInstance(mock_call.call_args_list[0][0][3], TimedOut)
        self.assertEqual(self.message.uuid, uuid)
        self.assertIn(self.message.uuid, node.pending)
        self.assertEqual(task, node.pending[self.message.uuid])
        self.assertEqual(1, len(task._callbacks))
        self.event_loop.call_soon(task.set_result, 'foo')
        self.event_loop.run_until_complete(blip())
        self.assertNotIn(self.message.uuid, node.pending)

    def test_send_message_fire_and_forget(self):
        """
        Ensure that the message is "sent" but does not appear in the local
        node's pending dict since the outgoing message is a fire-and-forget
        (i.e. there shouldn't be a pending task to resolve at some future
        point in time).
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        uuid, task = node.send_message(self.contact, self.message, True)
        self.connector.future.set_result('done')
        self.event_loop.run_until_complete(blip())
        self.assertEqual(self.message.uuid, uuid)
        self.assertEqual(True, task.done())
        self.event_loop.run_until_complete(blip())
        self.assertNotIn(self.message.uuid, node.pending)

    def test_send_message_bad_delivery(self):
        """
        Ensures that if the local node is unable to create a connection to the
        remote peer then the correct exception is set against the resulting
        Future and the remote peer is punished (for being unreliable).
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.routing_table.remove_contact = MagicMock()
        uuid, task = node.send_message(self.contact, self.message, True)
        self.connector.future.set_exception(Exception('Danger Will Robinson!'))
        self.event_loop.run_until_complete(blip())
        self.assertEqual(self.message.uuid, uuid)
        self.assertEqual(True, task.done())
        self.assertIsInstance(task.exception(), Exception)
        self.assertEqual('Danger Will Robinson!', task.exception().args[0])

    def test_send_ping(self):
        """
        Ensures a Ping message is correctly constructed and sent to the remote
        peer and a task to be resolved when the reply arrives is found in the
        local node's pending dict.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_ping(self.contact)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        self.assertIsInstance(node.send_message.call_args_list[0][0][1],
                              Ping)

    def test_send_pong(self):
        """
        Ensure a Pong message is correctly constructed and sent to the remote
        peer. A Pong is fire-and-forget.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_pong(self.message, self.contact)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        self.assertIsInstance(node.send_message.call_args_list[0][0][1],
                              Pong)
        faf = node.send_message.call_args_list[0][1]['fire_and_forget']
        self.assertEqual(faf, True)

    def test_send_store(self):
        """
        Ensure that a Store message is correctly constructed and sent to the
        remote peer.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_store(self.contact, self.message.key, self.message.value,
                        self.message.timestamp, self.message.expires,
                        self.message.created_with, self.message.public_key,
                        self.message.name, self.message.signature)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        msg = node.send_message.call_args_list[0][0][1]
        self.assertIsInstance(msg, Store)
        self.assertTrue(check_seal(msg))
        self.assertTrue(verify_item(to_dict(msg)))

    def test_send_find_nodes(self):
        """
        Ensure that a FindNode message is correctly constructed and sent to
        the remote peer.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_find(self.contact, self.message.key, FindNode)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        msg = node.send_message.call_args_list[0][0][1]
        self.assertIsInstance(msg, FindNode)

    def test_send_find_value(self):
        """
        Ensure that a FindValue message is correctly constructed and sent to
        the remote peer.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_find(self.contact, self.message.key, FindValue)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        msg = node.send_message.call_args_list[0][0][1]
        self.assertIsInstance(msg, FindValue)

    def test_send_value(self):
        """
        Ensure that a Value message is correctly constructed and sent to
        the remote peer. A Value message is fire-and-forget.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        node.send_value(self.message, self.contact, self.message.key,
                        self.message.value, self.message.timestamp,
                        self.message.expires, self.message.created_with,
                        self.message.public_key, self.message.name,
                        self.message.signature)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        msg = node.send_message.call_args_list[0][0][1]
        self.assertIsInstance(msg, Value)
        self.assertTrue(check_seal(msg))
        self.assertTrue(verify_item(to_dict(msg)))
        faf = node.send_message.call_args_list[0][1]['fire_and_forget']
        self.assertEqual(faf, True)

    def test_send_nodes(self):
        """
        Ensure that Nodes message is correctly constructed and sent to the
        remote peer. A Nodes message is fire-and-forget.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_message = MagicMock()
        nodes = ((PUBLIC_KEY, self.version, 'http://192.168.0.1:1908/'),)
        node.send_nodes(self.message, self.contact, nodes)
        self.assertEqual(1, node.send_message.call_count)
        self.assertEqual(node.send_message.call_args_list[0][0][0],
                         self.contact)
        msg = node.send_message.call_args_list[0][0][1]
        self.assertIsInstance(msg, Nodes)
        faf = node.send_message.call_args_list[0][1]['fire_and_forget']
        self.assertEqual(faf, True)

    def test_store_to_nodes(self):
        """
        Ensure that the correct number of send_store calls are made given an
        item to store, a list of target nodes and a duplication count
        (representing the number of nodes the item is to be duplicated to).
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_store = MagicMock(return_value=(str(uuid.uuid4()),
                                    asyncio.Future()))
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contacts.append(contact)
        result = node._store_to_nodes(contacts, 20, self.key, self.value,
                                      self.timestamp, self.expires,
                                      self.created_with, self.public_key,
                                      self.name, self.signature)
        self.assertEqual(20, node.send_store.call_count)
        self.assertEqual(20, len(result))
        for i in result:
            self.assertIsInstance(i, asyncio.Future)

    def test_store_to_nodes_duplicate_too_high(self):
        """
        Check that if the duplication count is higher than the available number
        of closest nodes then only the correct number of available nodes will
        be called.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_store = MagicMock(return_value=(str(uuid.uuid4()),
                                    asyncio.Future()))
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contacts.append(contact)
        result = node._store_to_nodes(contacts, 200, self.key, self.value,
                                      self.timestamp, self.expires,
                                      self.created_with, self.public_key,
                                      self.name, self.signature)
        self.assertEqual(20, node.send_store.call_count)
        self.assertEqual(20, len(result))

    def test_store_to_nodes_duplicate_lower_than_available(self):
        """
        Check that if the duplication count is lower than the available number
        of closest nodes then only duplication number of available nodes will
        be called.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_store = MagicMock(return_value=(str(uuid.uuid4()),
                                    asyncio.Future()))
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contacts.append(contact)
        result = node._store_to_nodes(contacts, 2, self.key, self.value,
                                      self.timestamp, self.expires,
                                      self.created_with, self.public_key,
                                      self.name, self.signature)
        self.assertEqual(2, node.send_store.call_count)
        self.assertEqual(2, len(result))

    def test_store_to_nodes_invalid_duplicate(self):
        """
        Ensure duplication value of 1 or more.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_store = MagicMock(return_value=(str(uuid.uuid4()),
                                    asyncio.Future()))
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contacts.append(contact)
        with self.assertRaises(ValueError):
            result = node._store_to_nodes(contacts, 0, self.key, self.value,
                                          self.timestamp, self.expires,
                                          self.created_with, self.public_key,
                                          self.name, self.signature)
        result = node._store_to_nodes(contacts, 1, self.key, self.value,
                                      self.timestamp, self.expires,
                                      self.created_with, self.public_key,
                                      self.name, self.signature)
        self.assertEqual(1, node.send_store.call_count)
        self.assertEqual(1, len(result))

    def test_store_to_nodes_invalid_nearest_nodes(self):
        """
        Ensure list of nearest nodes must contain something.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.send_store = MagicMock(return_value=asyncio.Future())
        with self.assertRaises(ValueError):
            node._store_to_nodes([], 20, self.key, self.value, self.timestamp,
                                 self.expires, self.created_with,
                                 self.public_key, self.name, self.signature)

    def test_replicate_returns_a_future(self):
        """
        Ensure a call to replicate returns an asyncio.Future.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)
        patcher = patch('drogulus.dht.node.Lookup._lookup')
        patcher.start()
        result = node.replicate(20, self.key, self.value, self.timestamp,
                                self.expires, self.created_with,
                                self.public_key, self.name, self.signature)
        self.assertIsInstance(result, asyncio.Future)
        patcher.stop()

    def test_replicate_barfs_bad_duplicate(self):
        """
        Ensure a call to replicate must use a valid (positive integer)
        duplicate value.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        patcher = patch('drogulus.dht.node.Lookup._lookup')
        patcher.start()
        with self.assertRaises(ValueError):
            node.replicate(0, self.key, self.value, self.timestamp,
                           self.expires, self.created_with,
                           self.public_key, self.name, self.signature)
        patcher.stop()

    def test_replicate_returns_a_future_empty_routing_table(self):
        """
        Ensure a call to replicate returns an asyncio.Future that has the
        expected exception as it's result if the routing table is empty.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        result = node.replicate(20, self.key, self.value, self.timestamp,
                                self.expires, self.created_with,
                                self.public_key, self.name, self.signature)
        self.assertIsInstance(result, asyncio.Future)
        self.assertTrue(result.done())
        with self.assertRaises(RoutingTableEmpty):
            result.result()

    def test_replicate_creates_lookup_with_expected_values(self):
        """
        Ensure the Lookup object is created properly.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)
        return_val = asyncio.Future()
        patcher = patch('drogulus.dht.node.Lookup',
                        return_value=return_val)
        mock_lookup = patcher.start()
        node.replicate(20, self.key, self.value, self.timestamp, self.expires,
                       self.created_with, self.public_key, self.name,
                       self.signature)
        patcher.stop()
        expected_target = construct_key(PUBLIC_KEY, self.name)
        mock_lookup.assert_called_once_with(FindNode, expected_target, node,
                                            node.event_loop)

    def test_replicate_future_resolves_with_expected_task_list(self):
        """
        Make sure the Future returned from replicate is fired with a list of
        the expected lentth when the Lookup instance completes.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/' % i
            contact = PeerNode(str(i), self.version, uri, 0)
            node.routing_table.add_contact(contact)
            contacts.append((PUBLIC_KEY, self.version, uri))
        nodes = tuple(contacts)

        def side_effect(*args):
            """
            Ensures the mock_send_find returns something useful.
            """
            u = str(uuid.uuid4())
            task = asyncio.Future()
            msg_dict = {
                'uuid': u,
                'recipient': PUBLIC_KEY,
                'sender': PUBLIC_KEY,
                'reply_port': 1908,
                'version': self.version,
                'nodes': nodes
            }
            seal = get_seal(msg_dict, PRIVATE_KEY)
            msg_dict['seal'] = seal
            msg_dict['message'] = 'nodes'
            message = from_dict(msg_dict)
            task.set_result(message)
            return (u, task)

        node.send_find = MagicMock(side_effect=side_effect)
        result = node.replicate(20, self.key, self.value, self.timestamp,
                                self.expires, self.created_with,
                                self.public_key, self.name, self.signature)

        def check_result(res):
            """
            Checks the Future is resolved with the expected values.
            """
            self.assertIsInstance(res.result(), list)
            for i in res.result():
                self.assertIsInstance(i, asyncio.Future)

        result.add_done_callback(check_result)
        self.event_loop.run_until_complete(result)
        self.assertTrue(result.done())

    def test_replicate_future_resolves_with_expected_exception(self):
        """
        Make sure the Future returned from replicate is fired with a the
        correct exception if the Lookup instance encountered an error.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        contacts = []
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/' % i
            contact = PeerNode(str(i), self.version, uri, 0)
            node.routing_table.add_contact(contact)
            contacts.append((PUBLIC_KEY, self.version, uri))
        nodes = tuple(contacts)

        def side_effect(*args):
            """
            Ensures the mock_send_find returns something useful.
            """
            u = str(uuid.uuid4())
            task = asyncio.Future()
            msg_dict = {
                'uuid': u,
                'recipient': PUBLIC_KEY,
                'sender': PUBLIC_KEY,
                'reply_port': 1908,
                'version': self.version,
                'nodes': nodes
            }
            seal = get_seal(msg_dict, PRIVATE_KEY)
            msg_dict['seal'] = seal
            msg_dict['message'] = 'nodes'
            message = from_dict(msg_dict)
            task.set_result(message)
            return (u, task)

        node.send_find = MagicMock(side_effect=side_effect)
        return_val = asyncio.Future()
        patcher = patch('drogulus.dht.node.Lookup',
                        return_value=return_val)
        patcher.start()
        result = node.replicate(20, self.key, self.value, self.timestamp,
                                self.expires, self.created_with,
                                self.public_key, self.name, self.signature)

        def check_result(res):
            """
            Checks the Future is resolved with the expected values.
            """
            self.assertIsInstance(res.exception(), ValueError)
            self.assertEqual('Test', res.exception().args[0])

        result.add_done_callback(check_result)
        return_val.set_exception(ValueError('Test'))
        self.event_loop.run_until_complete(blip())
        self.assertTrue(result.done())
        patcher.stop()

    def test_retrieve_returns_a_future(self):
        """
        Ensure a call to retrieve returns an asyncio.Future.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)
        patcher = patch('drogulus.dht.node.Lookup._lookup')
        patcher.start()
        result = node.replicate(20, self.key, self.value, self.timestamp,
                                self.expires, self.created_with,
                                self.public_key, self.name, self.signature)
        self.assertIsInstance(result, asyncio.Future)
        patcher.stop()

    def test_retrieve_returns_a_future_empty_routing_table(self):
        """
        Ensure a call to retrieve returns an asyncio.Future that has the
        expected exception as it's result if the node's routing table is empty.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        result = node.retrieve(self.key)
        self.assertIsInstance(result, asyncio.Future)
        self.assertTrue(result.done())
        with self.assertRaises(RoutingTableEmpty):
            result.result()

    def test_retrieve_with_a_result(self):
        """
        Ensure the retrieval of a value sets the correct result for the
        lookup Future.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            u = str(uuid.uuid4())
            task = asyncio.Future()
            return (u, task)

        node.send_find = MagicMock(side_effect=side_effect)
        key = self.message.key
        lookup = node.retrieve(key)
        node.send_store = MagicMock()

        uid = [i for i in lookup.pending_requests.keys()][0]
        contact = lookup.shortlist[0]
        response = asyncio.Future()
        response.set_result(self.message)
        lookup._handle_response(uid, contact, response)
        self.event_loop.run_until_complete(blip())
        self.assertTrue(lookup.done())
        self.assertEqual(self.message, lookup.result())

    def test_retrieve_causes_caching(self):
        """
        Ensure the retrieval of a value causes the caching of the found
        value to the node closest to the key that DID NOT return the value.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            u = str(uuid.uuid4())
            task = asyncio.Future()
            return (u, task)

        node.send_find = MagicMock(side_effect=side_effect)
        key = self.message.key
        lookup = node.retrieve(key)
        node.send_store = MagicMock()

        uid = [i for i in lookup.pending_requests.keys()][0]
        contact = lookup.shortlist[0]
        response = asyncio.Future()
        response.set_result(self.message)
        lookup._handle_response(uid, contact, response)
        self.event_loop.run_until_complete(blip())
        self.assertEqual(1, node.send_store.call_count)
        closest_contact = lookup.shortlist[0]
        node.send_store.assert_called_once_with(closest_contact,
                                                self.message.key,
                                                self.message.value,
                                                self.message.timestamp,
                                                self.message.expires,
                                                self.message.created_with,
                                                self.message.public_key,
                                                self.message.name,
                                                self.message.signature)

    def test_retrieve_with_bad_result(self):
        """
        If the result is not found or bad in some way (i.e. the lookup has
        an exception set) ensure that the caching doesn't occur.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        for i in range(20):
            uri = 'http://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            node.routing_table.add_contact(contact)

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            u = str(uuid.uuid4())
            task = asyncio.Future()
            return (u, task)

        node.send_find = MagicMock(side_effect=side_effect)
        key = self.message.key
        lookup = node.retrieve(key)
        node.send_store = MagicMock()
        ex = Exception('A test exception')
        lookup.set_exception(ex)
        self.event_loop.run_until_complete(blip())
        self.assertEqual(0, node.send_store.call_count)

    def test_refresh(self):
        """
        Ensure that the refresh method sends the required number of lookups to
        keep the routing table fresh.
        """
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        bucket1 = Bucket(1, 99999999)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.last_accessed = time.time() - 3700
        node.routing_table._buckets[0] = bucket1
        bucket2 = Bucket(99999999, 9999999999)
        # Bucket 2 will not need refreshing.
        bucket2.last_accessed = time.time()
        node.routing_table._buckets.append(bucket2)
        node.routing_table.get_refresh_list(0)
        lookup_patcher = patch('drogulus.dht.node.Lookup')
        mock_lookup = lookup_patcher.start()
        with patch.object(self.event_loop, 'call_later') as mock_call:
            node.refresh()
            mock_call.assert_called_once_with(REFRESH_INTERVAL, node.refresh)
        self.assertEqual(1, mock_lookup.call_count)
        lookup_patcher.stop()

    def test_republish_no_item(self):
        """
        Check that the republish check works when the affected item has
        already been removed from the data store.
        """
        patcher = patch('drogulus.dht.node.logging.info')
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        mock_log = patcher.start()
        node.republish('foo')
        self.assertEqual(2, mock_log.call_count)
        expected = 'Republish check for key: foo'
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        expected = 'foo no longer in local data store. Cancelled.'
        self.assertEqual(expected, mock_log.call_args_list[1][0][0])
        patcher.stop()

    def test_republish_item_expired(self):
        """
        Check that the republish check works as expected if the affected item
        has expired.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        # Signed item with out of date expires argument.
        signed_item['expires'] = 123.456
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.data_store[message.key] = message
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        node.republish(message.key)
        self.assertEqual(2, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        msg = '%s expired. Deleted from local data store.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[1][0][0])
        patcher.stop()

    def test_republish_item_zero_expiry(self):
        """
        If the item's expiry value is 0 then it should never expire.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.replicate = MagicMock()
        node.data_store[message.key] = message
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        mock_handler = MagicMock()
        with patch.object(self.event_loop, 'call_later',
                          return_value=mock_handler) as mock_call:
            node.republish(message.key)
            mock_call.assert_called_once_with(REPLICATE_INTERVAL,
                                              node.republish, message.key)
        self.assertEqual(2, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        msg = 'Removing %s due to lack of activity.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[1][0][0])
        patcher.stop()

    def test_republish_needs_replication(self):
        """
        Check that the republish check kicks off replication if the
        value has not been updated within REPLICATE_INTERVAL seconds.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.replicate = MagicMock()
        now = time.time()
        node.data_store._set_item(message.key, (message, 123.45, now))
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        mock_handler = MagicMock()
        with patch.object(self.event_loop, 'call_later',
                          return_value=mock_handler) as mock_call:
            node.republish(message.key)
            mock_call.assert_called_once_with(REPLICATE_INTERVAL,
                                              node.republish, message.key)
        self.assertEqual(2, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        msg = 'Republishing item %s.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[1][0][0])
        patcher.stop()

    def test_republish_no_replication_was_accessed(self):
        """
        Check that the republish check works as expected if the value HAS
        been updated within REPLICATE_INTERVAL seconds and the value HAS also
        been accessed within REPLICATE_INTERVAL seconds.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.replicate = MagicMock()
        now = time.time()
        node.data_store._set_item(message.key, (message, now, now))
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        mock_handler = MagicMock()
        with patch.object(self.event_loop, 'call_later',
                          return_value=mock_handler) as mock_call:
            node.republish(message.key)
            mock_call.assert_called_once_with(REPLICATE_INTERVAL,
                                              node.republish, message.key)
        self.assertEqual(1, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        patcher.stop()

    def test_republish_replication_lack_of_activity(self):
        """
        Check that the republish check kicks off replication if the
        value has not been updated within REPLICATE_INTERVAL seconds. Also
        ensure that if the value has NOT been accessed within
        REPLICATE_INTERVAL seconds then remove it from the local data store.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.replicate = MagicMock()
        node.data_store._set_item(message.key, (message, 123.45, 123.45))
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        mock_handler = MagicMock()
        mock_handler.cancel = MagicMock()
        with patch.object(self.event_loop, 'call_later',
                          return_value=mock_handler) as mock_call:
            node.republish(message.key)
            mock_call.assert_called_once_with(REPLICATE_INTERVAL,
                                              node.republish, message.key)
        self.assertEqual(3, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        msg = 'Republishing item %s.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[1][0][0])
        msg = 'Removing %s due to lack of activity.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[2][0][0])
        self.assertEqual(1, mock_handler.cancel.call_count)
        patcher.stop()

    def test_republish_no_replication_lack_of_activity(self):
        """
        Check that the republish check works as expected if the value HAS
        been updated within REPLICATE_INTERVAL seconds. Also ensure that if
        the value has NOT been accessed within REPLICATE_INTERVAL seconds then
        remove it from the local data store only after a replication has been
        kicked off.
        """
        signed_item = get_signed_item(self.name, self.value, PUBLIC_KEY,
                                      PRIVATE_KEY, 0)
        signed_item['uuid'] = self.uuid
        signed_item['sender'] = self.sender
        signed_item['recipient'] = self.recipient
        signed_item['reply_port'] = self.reply_port
        signed_item['version'] = self.version
        seal = get_seal(signed_item, PRIVATE_KEY)
        signed_item['seal'] = seal
        signed_item['message'] = 'store'
        message = from_dict(signed_item)
        node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop, self.connector,
                    self.reply_port)
        node.replicate = MagicMock()
        node.data_store[message.key] = message
        patcher = patch('drogulus.dht.node.logging.info')
        mock_log = patcher.start()
        mock_handler = MagicMock()
        mock_handler.cancel = MagicMock()
        with patch.object(self.event_loop, 'call_later',
                          return_value=mock_handler) as mock_call:
            node.republish(message.key)
            mock_call.assert_called_once_with(REPLICATE_INTERVAL,
                                              node.republish, message.key)
        self.assertEqual(2, mock_log.call_count)
        expected = 'Republish check for key: %s' % message.key
        self.assertEqual(expected, mock_log.call_args_list[0][0][0])
        msg = 'Removing %s due to lack of activity.' % message.key
        self.assertEqual(msg, mock_log.call_args_list[1][0][0])
        self.assertEqual(1, mock_handler.cancel.call_count)
        patcher.stop()
