# -*- coding: utf-8 -*-
"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import timeout, Node
from drogulus.constants import ERRORS, RPC_TIMEOUT
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus.net.protocol import DHTFactory
from drogulus.net.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value)
from drogulus.crypto import construct_key
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.python import log
from twisted.internet import defer, task
from mock import MagicMock, patch
from uuid import uuid4
import time


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQ
LN2RbbDIMHILA1i6wByXkqEamnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjG
b+oGVTKizfbMbGCKZ8fT64ZZgan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M
6WixkMTbFM91fW0mUwIDAQAB
-----END PUBLIC KEY-----"""


class FakeClient(object):
    """
    A class that pretends to be a client endpoint returned by Twisted's
    clientFromString. To be used with the mocks.
    """

    def __init__(self, protocol, success=True):
        """
        The protocol instance is set up as a fake by the test class. The
        success flag indicates if the client is to be able to connect
        successfully.
        """
        self.protocol = protocol
        self.success = True

    def connect(self, factory):
        d = defer.Deferred()
        if self.success:
            d.callback(self.protocol)
        else:
            d.errback()
        return d


def fakeAbortConnection():
    """
    Fakes the abortConnection method to be attached to the StringTransport used
    in the tests below.
    """
    pass


class TestTimeout(unittest.TestCase):
    """
    Ensures the timeout function works correctly.
    """

    def setUp(self):
        self.node_id = '1234567890abc'
        self.node = Node(self.node_id)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)
        self.uuid = str(uuid4())

    def test_timeout(self):
        """
        Test the good case.
        """
        self.protocol.transport.abortConnection = MagicMock()
        pending = {}
        deferred = defer.Deferred()
        pending[self.uuid] = deferred
        timeout(self.uuid, self.protocol, pending)
        # The record associated with the uuid has been removed from the pending
        # dictionary.
        self.assertEqual({}, pending)
        # The deferred has been cancelled.
        self.assertIsInstance(deferred.result.value, defer.CancelledError)
        # abortConnection() has been called once.
        self.assertEqual(1, self.protocol.transport.abortConnection.call_count)

    def test_timout_missing(self):
        """
        Ensure no state is changed if the message's uuid is missing from the
        pending dict.
        """
        # There is no change in the number of messages in the pending
        # dictionary.
        pending = {}
        pending[self.uuid] = 'a deferred'
        another_uuid = str(uuid4())
        timeout(another_uuid, self.protocol, pending)
        self.assertIn(self.uuid, pending)

    def test_timeout_with_parsing_payload(self):
        """
        Ensure that if the protocol is in a PARSING_PAYLOAD state then the
        message is not timed out because it is getting data from the remote
        peer.
        """
        # There is no change in the number of messages in the pending
        # dictionary.
        pending = {}
        pending[self.uuid] = 'a deferred'
        self.protocol._state = self.protocol._PARSING_PAYLOAD
        timeout(self.uuid, self.protocol, pending)
        self.assertIn(self.uuid, pending)


class TestNode(unittest.TestCase):
    """
    Ensures the Node class works as expected.
    """

    def setUp(self):
        """
        Following the pattern explained here:

        http://twistedmatrix.com/documents/current/core/howto/trial.html
        """
        self.node_id = '1234567890abc'
        self.node = Node(self.node_id)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.transport.abortConnection = fakeAbortConnection
        self.protocol.makeConnection(self.transport)
        self.clock = task.Clock()
        self.protocol.callLater = self.clock.callLater
        self.value = 'value'
        self.signature = ('\x882f\xf9A\xcd\xf9\xb1\xcc\xdbl\x1c\xb2\xdb' +
                          '\xa3UQ\x9a\x08\x96\x12\x83^d\xd8M\xc2`\x81Hz' +
                          '\x84~\xf4\x9d\x0e\xbd\x81\xc4/\x94\x9dfg\xb2aq' +
                          '\xa6\xf8!k\x94\x0c\x9b\xb5\x8e \xcd\xfb\x87' +
                          '\x83`wu\xeb\xf2\x19\xd6X\xdd\xb3\x98\xb5\xbc#B' +
                          '\xe3\n\x85G\xb4\x9c\x9b\xb0-\xd2B\x83W\xb8\xca' +
                          '\xecv\xa9\xc4\x9d\xd8\xd0\xf1&\x1a\xfaw\xa0\x99' +
                          '\x1b\x84\xdad$\xebO\x1a\x9e:w\x14d_\xe3\x03#\x95' +
                          '\x9d\x10B\xe7\x13')
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
        self.assertEqual({}, node._pending)
        self.assertEqual('ssl:%s:%d', node._client_string)
        self.assertEqual(get_version(), node.version)

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
        # Check it results in a call to the routing table's add_contact method.
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
        # Check it results in a call to the node's handle_ping method.
        self.node.handle_ping.assert_called_once_with(msg, self.protocol)

    def test_message_received_store(self):
        """
        Ensures a Store message is handled correctly.
        """
        self.node.handle_store = MagicMock()
        # Create a simple Store message.
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Check it results in a call to the node's handle_store method.
        self.node.handle_store.assert_called_once_with(msg, self.protocol,
                                                       contact)

    def test_message_received_find_node(self):
        """
        Ensures a FindNode message is handled correctly.
        """
        self.node.handle_find_node = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        msg = FindNode(uuid, self.node_id, key, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_find_node method.
        self.node.handle_find_node.assert_called_once_with(msg, self.protocol)

    def test_message_received_find_value(self):
        """
        Ensures a FindValue message is handled correctly.
        """
        self.node.handle_find_value = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        key = '12345abc'
        msg = FindValue(uuid, self.node_id, key, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_find_value method.
        self.node.handle_find_value.assert_called_once_with(msg, self.protocol)

    def test_message_received_error(self):
        """
        Ensures an Error message is handled correctly.
        """
        self.node.handle_error = MagicMock()
        # Create an Error message.
        uuid = str(uuid4())
        version = get_version()
        code = 1
        title = ERRORS[code]
        details = {'foo': 'bar'}
        msg = Error(uuid, self.node_id, code, title, details, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Check it results in a call to the node's handle_error method.
        self.node.handle_error.assert_called_once_with(msg, self.protocol,
                                                       contact)

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
        Ensures the handle_ping method loses the connection after sending the
        Pong.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_ping(msg, self.protocol)
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

    def test_handle_store_old_value(self):
        """
        Ensures that a Store message containing an out-of-date version of a
        value already known to the node is handled correctly:

        * The current up-to-date value is not overwritten.
        * The node responds with an appropriate error message.
        """
        # Create existing up-to-date value
        newer_msg = Store(self.uuid, self.node.id, self.key, self.value,
                          self.timestamp, self.expires, PUBLIC_KEY, self.name,
                          self.meta, self.signature, self.version)
        self.node._data_store.set_item(newer_msg.key, newer_msg)
        # Incoming message and peer
        old_timestamp = self.timestamp - 9999
        old_value = 'old value'
        old_sig = ('\t^#F:\x0c;\r{Z\xbd$\xe4\xffz}\xb6Q\xb3g6\xca,\xe8' +
                   '\xe4eY<g\x92tN\x8f\xbe\x8fs|\xdf\xe5O\xc6eZ\xef\xf5' +
                   '\xd8\xab?g\xd7y\x81\xbeB\\\xe0=\xd1{\xcc\x0f%#\x9ad' +
                   '\xcf\xea\xbd\x95\x0e\xed\xd7\x98\xfc\x85O\x81\x15' +
                   '\x18/\xcb\xa0\x01\x1f+\x12\x8e\xdc\xbf\x9a\r\xd6\xfb' +
                   '\xe0\xab\xc9\xff\xb5\xe5\x18\xb8\xe9\x8c\x13\xd1\xa5' +
                   '\xba\xeb\xfa\xce\xaaT\xc8\x8c:\xcd\xc7\x0c\xfdCD\x00' +
                   '\xd9\x93\xfeo><')
        old_msg = Store(self.uuid, self.node.id, self.key, old_value,
                        old_timestamp, self.expires, PUBLIC_KEY, self.name,
                        self.meta, old_sig, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        # Check for the expected exception.
        ex = self.assertRaises(ValueError, self.node.handle_store, old_msg,
                               self.protocol, other_node)
        details = {
            'new_timestamp': '%d' % self.timestamp
        }
        self.assertEqual(ex.args[0], 8)
        self.assertEqual(ex.args[1], ERRORS[8])
        self.assertEqual(ex.args[2], details)
        self.assertEqual(ex.args[3], self.uuid)
        # Ensure the original message is in local storage.
        self.assertIn(self.key, self.node._data_store)
        self.assertEqual(newer_msg, self.node._data_store[self.key])

    def test_handle_store_new_value(self):
        """
        Ensures that a Store message containing a new version of a
        value already known to the node is handled correctly.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Create existing up-to-date value
        old_timestamp = self.timestamp - 9999
        old_value = 'old value'
        old_sig = ('\t^#F:\x0c;\r{Z\xbd$\xe4\xffz}\xb6Q\xb3g6\xca,\xe8' +
                   '\xe4eY<g\x92tN\x8f\xbe\x8fs|\xdf\xe5O\xc6eZ\xef\xf5' +
                   '\xd8\xab?g\xd7y\x81\xbeB\\\xe0=\xd1{\xcc\x0f%#\x9ad' +
                   '\xcf\xea\xbd\x95\x0e\xed\xd7\x98\xfc\x85O\x81\x15' +
                   '\x18/\xcb\xa0\x01\x1f+\x12\x8e\xdc\xbf\x9a\r\xd6\xfb' +
                   '\xe0\xab\xc9\xff\xb5\xe5\x18\xb8\xe9\x8c\x13\xd1\xa5' +
                   '\xba\xeb\xfa\xce\xaaT\xc8\x8c:\xcd\xc7\x0c\xfdCD\x00' +
                   '\xd9\x93\xfeo><')
        old_msg = Store(self.uuid, self.node.id, self.key, old_value,
                        old_timestamp, self.expires, PUBLIC_KEY, self.name,
                        self.meta, old_sig, self.version)
        self.node._data_store.set_item(old_msg.key, old_msg)
        self.assertIn(self.key, self.node._data_store)
        self.assertEqual(old_msg, self.node._data_store[self.key])
        # Incoming message and peer
        new_msg = Store(self.uuid, self.node.id, self.key, self.value,
                        self.timestamp, self.expires, PUBLIC_KEY, self.name,
                        self.meta, self.signature, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        # Store the new version of the message.
        self.node.handle_store(new_msg, self.protocol, other_node)
        # Ensure the message is in local storage.
        self.assertIn(self.key, self.node._data_store)
        self.assertEqual(new_msg, self.node._data_store[self.key])
        # Ensure the response is a Pong message.
        result = Pong(self.uuid, self.node.id, self.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_store_bad_message(self):
        """
        Ensures an invalid Store message is handled correctly.
        """
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
        ex = self.assertRaises(ValueError, self.node.handle_store, msg,
                               self.protocol, other_node)
        # Check the exception
        self.assertEqual(ex.args[0], 6)
        self.assertEqual(ex.args[1], ERRORS[6])
        details = {
            'message': 'You have been removed from remote routing table.'
        }
        self.assertEqual(ex.args[2], details)
        self.assertEqual(ex.args[3], self.uuid)
        # Ensure the message is not in local storage.
        self.assertNotIn(self.key, self.node._data_store)
        # Ensure the contact is not in the routing table
        self.assertEqual(0, len(self.node._routing_table._buckets[0]))

    def test_handle_store_loses_connection(self):
        """
        Ensures the handle_store method with a good Store message loses the
        connection after sending the Pong message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Incoming message and peer
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        self.node.handle_store(msg, self.protocol, other_node)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_find_nodes(self):
        """
        Ensure a valid FindNodes message is handled correctly.
        """
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Populate the routing table with contacts.
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            self.node._routing_table.add_contact(contact)
        # Incoming FindNode message
        msg = FindNode(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_node(msg, self.protocol)
        # Check the response sent back
        other_nodes = [(n.id, n.address, n.port, n.version) for n in
                       self.node._routing_table.find_close_nodes(self.key)]
        result = Nodes(msg.uuid, self.node.id, other_nodes, self.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_find_nodes_loses_connection(self):
        """
        Ensures the handle_find_nodes method loses the connection after
        sending the Nodes message.
        """
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Populate the routing table with contacts.
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            self.node._routing_table.add_contact(contact)
        # Incoming FindNode message
        msg = FindNode(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_node(msg, self.protocol)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_find_value_with_match(self):
        """
        Ensures the handle_find_value method responds with a matching Value
        message if the value exists in the datastore.
        """
        # Store value.
        val = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        self.node._data_store.set_item(val.key, val)
        # Mock
        self.protocol.sendMessage = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Check the response sent back
        result = Value(msg.uuid, self.node.id, val.key, val.value,
                       val.timestamp, val.expires, val.public_key, val.name,
                       val.meta, val.sig, val.version)
        self.protocol.sendMessage.assert_called_once_with(result, True)

    def test_handle_find_value_no_match(self):
        """
        Ensures the handle_find_value method calls the handle_find_nodes
        method with the correct values if no matching value exists in the
        local datastore.
        """
        # Mock
        self.node.handle_find_node = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Check the response sent back
        self.node.handle_find_node.assert_called_once_with(msg, self.protocol)

    def test_handle_find_value_loses_connection(self):
        """
        Ensures the handle_find_value method loses the connection after
        sending the a matched value.
        """
        # Store value.
        val = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        self.node._data_store.set_item(val.key, val)
        # Mock
        self.protocol.transport.loseConnection = MagicMock()
        # Incoming FindValue message
        msg = FindValue(self.uuid, self.node.id, self.key, self.version)
        self.node.handle_find_value(msg, self.protocol)
        # Ensure the loseConnection method was also called.
        self.protocol.transport.loseConnection.assert_called_once_with()

    def test_handle_error_writes_to_log(self):
        """
        Ensures the handle_error method writes details about the error to the
        log.
        """
        log.msg = MagicMock()
        # Create an Error message.
        uuid = str(uuid4())
        version = get_version()
        code = 1
        title = ERRORS[code]
        details = {'foo': 'bar'}
        msg = Error(uuid, self.node_id, code, title, details, version)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Receive it...
        self.node.handle_error(msg, self.protocol, contact)
        # Check it results in two calls to the log.msg method (one to signify
        # an error has happened, the other the actual error message).
        self.assertEqual(2, log.msg.call_count)

    def test_send_message(self):
        """
        Ensure send_message returns a deferred.
        """
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        # Check for the deferred.
        result = self.node.send_message(contact, msg)
        self.assertTrue(isinstance(result, defer.Deferred))

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_on_connect_adds_message_to_pending(self,
                                                             mock_client):
        """
        Ensure that when a connection is made the on_connect function wrapped
        inside send_message adds the message and deferred to the pending
        messages dictionary.
        """
        # Mock, mock, glorious mock; nothing quite like it to test a code
        # block. (To the tune of "Mud, mud, glorious mud!")
        mock_client.return_value = FakeClient(self.protocol)
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        deferred = self.node.send_message(contact, msg)
        self.assertIn(uuid, self.node._pending)
        self.assertEqual(self.node._pending[uuid], deferred)
        # Tidies up.
        self.clock.advance(RPC_TIMEOUT)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_timeout_call_later(self, mock_client):
        """
        Ensure that when a connection is made the on_connect function wrapped
        inside send_message calls callLater with the timeout function.
        """
        mock_client.return_value = FakeClient(self.protocol)
        # Mock the timeout function
        patcher = patch('drogulus.dht.node.timeout')
        mockTimeout = patcher.start()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        deferred = self.node.send_message(contact, msg)
        self.assertIn(uuid, self.node._pending)
        self.assertEqual(self.node._pending[uuid], deferred)
        self.clock.advance(RPC_TIMEOUT)
        # Ensure the timeout function was called
        self.assertEqual(1, mockTimeout.call_count)
        # Tidy up.
        patcher.stop()

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_sends_message(self, mock_client):
        """
        Ensure that the message passed in to send_message gets sent down the
        wire to the recipient.
        """
        mock_client.return_value = FakeClient(self.protocol)
        self.protocol.sendMessage = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        self.node.send_message(contact, msg)
        self.protocol.sendMessage.assert_called_once_with(msg)
        # Tidy up.
        self.clock.advance(RPC_TIMEOUT)
