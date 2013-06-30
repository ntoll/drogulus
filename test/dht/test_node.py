# -*- coding: utf-8 -*-
"""
Ensures code that represents a local node in the DHT network works as
expected
"""
from drogulus.dht.node import (RoutingTableEmpty, response_timeout, NodeLookup,
                               Node, ValueNotFound)
from drogulus.dht.routingtable import RoutingTable
from drogulus.constants import (ERRORS, RPC_TIMEOUT, RESPONSE_TIMEOUT, K,
                                REPLICATE_INTERVAL, ALPHA)
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus.net.protocol import DHTFactory
from drogulus.net.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value)
from drogulus.crypto import construct_key, generate_signature
from drogulus.utils import long_to_hex, sort_contacts
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.python import log
from twisted.internet import defer, task, reactor
from twisted.python.failure import Failure
from mock import MagicMock, patch
from uuid import uuid4
import time


# Useful throw-away constants for testing purposes.
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXgIBAAKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQLN2RbbDIMHILA1i6wByXkqEa
mnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjGb+oGVTKizfbMbGCKZ8fT64ZZ
gan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M6WixkMTbFM91fW0mUwIDAQAB
AoGBAJvBENvj5wH1W2dl0ShY9MLRpuxMjHogo3rfQr/G60AkavhaYfKn0MB4tPYh
MuCgtmF+ATqaWytbq9oUNVPnLUqqn5M9N86+Gb6z8ld+AcR2BD8oZ6tQaiEIGzmi
L9AWEZZnyluDSHMXDoVrvDLxPpKW0yPjvQfWN15QF+H79faJAkEA0hgdueFrZf3h
os59ukzNzQy4gjL5ea35azbQt2jTc+lDOu+yjUic2O7Os7oxnSArpujDiOkYgaih
Dny+/bIgLQJBAOhGKjhpafdpgpr/BjRlmUHXLaa+Zrp/S4RtkIEkE9XXkmQjvVZ3
EyN/h0IVNBv45lDK0Qztjic0L1GON62Z8H8CQAcRkqZ3ZCKpWRceNXK4NNBqVibj
SiuC4/psfLc/CqZCueVYvTwtrkFKP6Aiaprrwyw5dqK7nPx3zPtszQxCGv0CQQDK
51BGiz94VAE1qQYgi4g/zdshSD6xODYd7yBGz99L9M77D4V8nPRpFCRyA9fLf7ii
ZyoLYxHFCX80fUoCKvG9AkEAyX5iCi3aoLYd/CvOFYB2fcXzauKrhopS7/NruDk/
LluSlW3qpi1BGDHVTeWWj2sm30NAybTHjNOX7OxEZ1yVwg==
-----END RSA PRIVATE KEY-----"""


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

    def __init__(self, protocol, success=True, timeout=False,
                 replace_cancel=False):
        """
        The protocol instance is set up as a fake by the test class. The
        success flag indicates if the client is to be able to work
        successfully. The timeout flag indicates if the deferred is to fire
        as if a connection has been made.
        """
        self.protocol = protocol
        self.success = success
        self.timeout = timeout
        self.replace_cancel = replace_cancel
        if replace_cancel:
            self.cancel_function = MagicMock()

    def connect(self, factory):
        d = defer.Deferred()
        if self.timeout:
            # This is a hack to ensure the cancel method is within scope of the
            # test function (as an attribute of the FakeClient object to
            # ensure it has fired. :-(
            if self.replace_cancel:
                d.cancel = self.cancel_function
            return d
        else:
            if self.success:
                d.callback(self.protocol)
            else:
                d.errback(Exception("Error!"))
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

    def test_response_timeout(self):
        """
        Test the good case.
        """
        self.protocol.transport.abortConnection = MagicMock()
        self.node._routing_table.remove_contact = MagicMock()
        deferred = defer.Deferred()
        self.node._pending[self.uuid] = deferred
        # Create a simple Ping message.
        version = get_version()
        msg = Ping(self.uuid, self.node_id, version)
        response_timeout(msg, self.protocol, self.node)
        # The record associated with the uuid has been removed from the pending
        # dictionary.
        self.assertEqual({}, self.node._pending)
        # The deferred has been cancelled.
        self.assertIsInstance(deferred.result.value, defer.CancelledError)
        # abortConnection() has been called once.
        self.assertEqual(1, self.protocol.transport.abortConnection.call_count)
        # The remove_contact method of the routing table has been called once.
        self.node._routing_table.remove_contact.\
            assert_called_once_with(msg.node)

    def test_message_timout_missing(self):
        """
        Ensure no state is changed if the message's uuid is missing from the
        pending dict.
        """
        # There is no change in the number of messages in the pending
        # dictionary.
        self.node._pending[self.uuid] = 'a deferred'
        another_uuid = str(uuid4())
        version = get_version()
        msg = Ping(another_uuid, self.node_id, version)
        response_timeout(msg, self.protocol, self.node)
        self.assertIn(self.uuid, self.node._pending)


class TestNodeLookup(unittest.TestCase):
    """
    Ensures the NodeLookup class works as expected. See the NodeLookup class's
    documentation for a relatively simple explanation of how the class is
    supposed to function.
    """

    def setUp(self):
        """
        Following the pattern explained here:

        http://twistedmatrix.com/documents/current/core/howto/trial.html
        """
        self.node_id = '1234567890abc'
        self.node = Node(self.node_id)
        self.remote_node_count = 20
        for i in range(self.remote_node_count):
            contact = Contact(long_to_hex(i), '192.168.0.%d' % i, 9999,
                              self.node.version, 0)
            self.node._routing_table.add_contact(contact)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.transport.abortConnection = fakeAbortConnection
        self.protocol.makeConnection(self.transport)
        self.clock = task.Clock()
        reactor.callLater = self.clock.callLater
        self.value = 'value'
        self.uuid = str(uuid4())
        self.timestamp = time.time()
        self.expires = self.timestamp + 1000
        self.name = 'name'
        self.meta = {'meta': 'value'}
        self.signature = generate_signature(self.value, self.timestamp,
                                            self.expires, self.name, self.meta,
                                            PRIVATE_KEY)
        self.version = get_version()
        self.key = construct_key(PUBLIC_KEY, self.name)
        self.timeout = 1000
        self.target_key = long_to_hex(100)
        node_list = []
        for i in range(101, 121):
            contact_id = long_to_hex(i)
            contact_address = '192.168.1.%d' % i
            contact_port = 9999
            contact_version = self.version
            contact_last_seen = self.timestamp - (i * 100)
            contact = Contact(contact_id, contact_address, contact_port,
                              contact_version, contact_last_seen)
            node_list.append(contact)
        self.nodes = tuple(sort_contacts(node_list, self.target_key))

    def test_init(self):
        """
        The simplest case - ensure the object is set up correctly.
        """
        lookup = NodeLookup(self.key, FindNode, self.node)
        self.assertIsInstance(lookup, defer.Deferred)
        self.assertEqual(lookup.target, self.key)
        self.assertEqual(lookup.message_type, FindNode)
        self.assertEqual(lookup.local_node, self.node)
        self.assertIsInstance(lookup.contacted, set)
        self.assertIsInstance(lookup.pending_requests, dict)
        self.assertIsInstance(lookup.shortlist, list)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])

    def test_lookup_called_by_init(self, ):
        """
        Ensure that the __init__ method kicks off the lookup by calling the
        NodeLookup's _lookup method.
        """
        # Patch NodeLookup._lookup
        patcher = patch('drogulus.dht.node.NodeLookup._lookup')
        mock_lookup = patcher.start()
        NodeLookup(self.key, FindNode, self.node, self.timeout)
        self.assertEqual(1, mock_lookup.call_count)
        # Tidy up.
        patcher.stop()

    def test_init_timeout_called(self):
        """
        Ensure the cancel method is called after timeout seconds.
        """
        patcher = patch('drogulus.dht.node.NodeLookup._lookup')
        patcher.start()
        lookup = NodeLookup(self.key, FindNode, self.node, self.timeout)
        lookup.cancel = MagicMock()
        self.clock.advance(self.timeout)
        lookup.cancel.called_once_with(lookup)
        self.failureResultOf(lookup).trap(defer.CancelledError)
        patcher.stop()

    def test_init_finds_close_nodes(self):
        """
        Ensure that __init__ attempts to call find_close_nodes on the routing
        table.
        """
        self.node._routing_table.find_close_nodes = MagicMock()
        NodeLookup(self.key, FindNode, self.node)
        self.node._routing_table.find_close_nodes.\
            assert_called_once_with(self.key)

    def test_init_touches_kbucket(self):
        """
        If the target key is not the local node's id then touch_kbucket needs
        to be called to update the last_accessed attribute of the K-bucket
        containing the target key.
        """
        self.node._routing_table.touch_kbucket = MagicMock()
        NodeLookup(self.key, FindNode, self.node)
        self.node._routing_table.touch_kbucket.\
            assert_called_once_with(self.key)

    def test_init_skips_touch_kbucket_if_node_id_is_key(self):
        """
        The touch_kbucket operation only needs to happen if the target key is
        NOT the local node's id.
        """
        self.node._routing_table.touch_kbucket = MagicMock()
        NodeLookup(self.node.id, FindNode, self.node)
        self.assertEqual(0, self.node._routing_table.touch_kbucket.call_count)

    def test_init_no_known_nodes(self):
        """
        Checks that if the local node doesn't know of any other nodes then
        the resulting lookup calls back with a RoutingTableEmpty exception.
        """
        self.node._routing_table = RoutingTable(self.node.id)
        lookup = NodeLookup(self.key, FindNode, self.node)
        self.assertIsInstance(lookup, defer.Deferred)
        self.assertTrue(lookup.called)

        def errback_check(result):
            self.assertIsInstance(result.value, RoutingTableEmpty)

        lookup.addErrback(errback_check)

    def test_cancel_pending_requests(self):
        """
        Ensures any deferreds stored in self.pending_requests are cancelled.
        """
        # Avoids the creation of surplus to requirements deferreds during the
        # __init__ of the lookup object.
        patcher = patch('drogulus.dht.node.NodeLookup._lookup')
        patcher.start()
        lookup = NodeLookup(self.key, FindNode, self.node)
        d1 = defer.Deferred()
        d2 = defer.Deferred()
        d3 = defer.Deferred()
        errback1 = MagicMock()
        errback2 = MagicMock()
        errback3 = MagicMock()
        d1.addErrback(errback1)
        d2.addErrback(errback2)
        d3.addErrback(errback3)
        lookup.pending_requests[1] = d1
        lookup.pending_requests[2] = d2
        lookup.pending_requests[3] = d3
        lookup.cancel()
        self.assertEqual(1, errback1.call_count)
        self.assertIsInstance(errback1.call_args[0][0].value,
                              defer.CancelledError)
        self.assertEqual(1, errback2.call_count)
        self.assertIsInstance(errback2.call_args[0][0].value,
                              defer.CancelledError)
        self.assertEqual(1, errback3.call_count)
        self.assertIsInstance(errback3.call_args[0][0].value,
                              defer.CancelledError)
        self.assertEqual(0, len(lookup.pending_requests))
        # Tidy up.
        patcher.stop()

    def test_cancel(self):
        """
        Ensures the cancel function attempts to tidy up correctly.
        """
        errback = MagicMock()
        lookup = NodeLookup(self.key, FindNode, self.node)
        lookup._cancel_pending_requests = MagicMock()
        lookup.addErrback(errback)
        lookup.cancel()
        self.assertEqual(1, lookup._cancel_pending_requests.call_count)
        self.assertEqual(1, errback.call_count)
        self.assertIsInstance(errback.call_args[0][0].value,
                              defer.CancelledError)

    def test_lookup_none_pending_none_contacted(self):
        """
        Ensures the lookup method works with no pending requests nor any nodes
        previously contacted.
        """

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)

        lookup = NodeLookup(self.key, FindNode, self.node)
        # The _lookup method is called by __init__ from the state being checked
        # by this test (i.e. no pending requests or any previously contacted
        # nodes).
        self.assertEqual(ALPHA, self.node.send_find.call_count)
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        self.assertEqual(ALPHA, len(lookup.contacted))

    def test_lookup_some_pending_some_contacted(self):
        """
        Ensures the lookup method works with some pending slots available and
        some nodes previously contacted.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)

        lookup = NodeLookup(self.key, FindNode, self.node)
        # Reset the state of lookup.
        lookup.pending_requests = {}
        lookup.contacted = set()
        self.node.send_find.call_count = 0

        # Add a single pending request.
        pending_uuid = str(uuid4())
        pending_deferred = defer.Deferred()
        lookup.pending_requests[pending_uuid] = pending_deferred
        # Add a single contact to the contacted list.
        lookup.contacted.add(lookup.shortlist[0])
        # Test the state.
        self.assertEqual(1, len(lookup.pending_requests))
        self.assertEqual(1, len(lookup.contacted))

        # Re-run _lookup and test.
        lookup._lookup()
        self.assertEqual(ALPHA - 1, self.node.send_find.call_count)
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        self.assertEqual(ALPHA, len(lookup.contacted))

    def test_lookup_all_pending_some_contacted(self):
        """
        Ensures the lookup method works as expected with no more pending slots
        left available and some nodes previously contacted.

        This situation should never occur but I'm testing it to ensure the
        guard against sending surplus expensive network calls works.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)

        lookup = NodeLookup(self.key, FindNode, self.node)
        # Ensure we have a good starting state (all [ALPHA] pending_requests
        # slots are taken, only ALPHA nodes have been contacted, there are
        # still [K] candidate nodes in the shortlist).
        self.assertEqual(ALPHA, self.node.send_find.call_count)
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        self.assertEqual(ALPHA, len(lookup.contacted))
        self.assertEqual(K, len(lookup.shortlist))

        # Re-run _lookup and ensure no further network calls are made.
        lookup._lookup()
        self.assertEqual(ALPHA, self.node.send_find.call_count)

    def test_lookup_none_pending_all_contacted(self):
        """
        Ensures the lookup method works with no pending requests and all known
        nodes having previously been contacted.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)

        lookup = NodeLookup(self.key, FindNode, self.node)
        # Put lookup in the state to test.
        lookup.pending_requests = {}
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        self.node.send_find.call_count = 0

        # Re-run _lookup and test
        lookup._lookup()
        self.assertEqual(0, self.node.send_find.call_count)

    def test_lookup_adds_callback(self):
        """
        Ensures the lookup method adds the expected callback to the deferreds
        that represent requests to other nodes in the DHT.
        """
        patcher = patch('drogulus.dht.node.NodeLookup._handle_response')
        mock_handle_response = patcher.start()

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            deferred.callback("result")
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        NodeLookup(self.key, FindNode, self.node)
        # Check the expected callbacks have been called correctly
        self.assertEqual(ALPHA, mock_handle_response.call_count)
        # Ensure the errback was called with the expected values
        # Arg 1 = string (uuid).
        self.assertEqual(str, mock_handle_response.call_args[0][0].__class__)
        # Arg 2 = Contact instance.
        self.assertEqual(Contact,
                         mock_handle_response.call_args[0][1].__class__)
        # Arg 3 = result.
        self.assertEqual("result", mock_handle_response.call_args[0][2])
        # Tidy up.
        patcher.stop()

    def test_lookup_adds_errback(self):
        """
        Ensures the lookup method adds the expected errback to the deferreds
        that represent requests to other nodes in the DHT.
        """
        patcher = patch('drogulus.dht.node.NodeLookup._handle_error')
        mock_handle_error = patcher.start()

        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            deferred.errback(Exception('Error'))
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        NodeLookup(self.key, FindNode, self.node)
        # Check the expected errbacks have been called correctly
        self.assertEqual(ALPHA, mock_handle_error.call_count)
        # Ensure the errback was called with the expected values
        # Arg 1 = string (uuid).
        self.assertEqual(str, mock_handle_error.call_args[0][0].__class__)
        # Arg 2 = Contact instance.
        self.assertEqual(Contact, mock_handle_error.call_args[0][1].__class__)
        # Arg 3 = Failure instance (to wrap the exception).
        self.assertEqual(Failure, mock_handle_error.call_args[0][2].__class__)
        # Tidy up.
        patcher.stop()

    def test_handle_error(self):
        """
        Ensures the _handle_error function works as expected and cleans things
        up / continues the lookup.

        If a node doesn't reply or an error is encountered it is removed from
        self.shortlist and self.pending_requests. Start the _lookup again.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)
        # Ensure there is a good start condition.
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        shortlist_length = len(lookup.shortlist)

        lookup._lookup = MagicMock()
        deferred = lookup.pending_requests[lookup.pending_requests.keys()[0]]
        deferred.errback(Exception())
        self.assertEqual(ALPHA - 1, len(lookup.pending_requests))
        self.assertEqual(shortlist_length - 1, len(lookup.shortlist))
        self.assertEqual(1, lookup._lookup.call_count)

    def test_handle_error_not_in_shortlist(self):
        """
        Ensures that there is no error thrown if the request that caused the
        error is not in the shortlist any more. This should never happen but
        the test is included to check the guard.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)
        # Ensure there is a good start condition.
        self.assertEqual(ALPHA, len(lookup.pending_requests))

        lookup._lookup = MagicMock()
        deferred = lookup.pending_requests[lookup.pending_requests.keys()[0]]
        # Remove all the contacts from the shortlist
        lookup.shortlist = []
        deferred.errback(Exception())
        # No error! Pending requests has been processed correctly and there is
        # no change to the shortlist. Since only one deferred was fired then
        # _lookup should only have been called once.
        self.assertEqual(ALPHA - 1, len(lookup.pending_requests))
        self.assertEqual(0, len(lookup.shortlist))
        self.assertEqual(1, lookup._lookup.call_count)

    def test_handle_error_not_in_pending_requests(self):
        """
        Ensures that there is no error thrown if the request that caused the
        error is not in the pending_requests dict any more. This should never
        happen but the test is included to check the guard.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)
        # Ensure there is a good start condition.
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        shortlist_length = len(lookup.shortlist)

        lookup._lookup = MagicMock()
        deferred = lookup.pending_requests[lookup.pending_requests.keys()[0]]
        # Remove all the contacts from the pending_requests
        lookup.pending_requests = {}
        deferred.errback(Exception())
        # No error!
        self.assertEqual(0, len(lookup.pending_requests))
        self.assertEqual(shortlist_length - 1, len(lookup.shortlist))
        self.assertEqual(1, lookup._lookup.call_count)

    def test_blacklist(self):
        """
        Make sure that the NodeLookup's blacklist method works as expected: the
        misbehaving peer is removed from the shortlist and added to the routing
        table's "global" blacklist.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)

        problem_contact = lookup.shortlist[0]
        self.node._routing_table.blacklist = MagicMock()
        lookup._blacklist(problem_contact)
        self.assertNotIn(problem_contact, lookup.shortlist)
        self.assertEqual(1, self.node._routing_table.blacklist.call_count)

    def test_handle_response_wrong_message_type(self):
        """
        Ensure that something that's not a Find[Node|Value] message results in
        the responding contact being blacklisted and an exception being thrown.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        version = get_version()
        msg = Ping(uuid, self.node_id, version)

        lookup._blacklist = MagicMock()
        ex = self.assertRaises(TypeError, lookup._handle_response, uuid,
                               contact, msg)
        self.assertEqual('Unexpected response type from %r' % contact,
                         ex.message)
        lookup._blacklist.assert_called_once_with(contact)

    def test_handle_response_wrong_value_for_findnode_message(self):
        """
        Ensures that if a Value response is returned for a FindNode request
        then the misbehaving peer is blacklisted and an exception is thrown.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindNode, self.node)

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Value(uuid, self.node.id, self.key, self.value, self.timestamp,
                    self.expires, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.node.version)
        lookup._blacklist = MagicMock()
        ex = self.assertRaises(TypeError, lookup._handle_response, uuid,
                               contact, msg)
        self.assertEqual('Unexpected response type from %r' % contact,
                         ex.message)
        lookup._blacklist.assert_called_once_with(contact)

    def test_handle_response_request_removed_from_pending_requests(self):
        """
        Ensure the pending request that triggered the response being handled by
        the callback is removed from the pending_requests.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindValue, self.node)

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Value(uuid, self.node.id, self.key, self.value, self.timestamp,
                    self.expires, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        self.assertNotIn(uuid, lookup.pending_requests.keys())

    def test_handle_response_value_results_in_node_lookup_callback(self):
        """
        Ensures that if a valid Value message is being handled then all other
        pending requests are cancelled and the NodeLookup object calls back
        with the passed in Value object.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindValue, self.node)

        uuid = lookup.pending_requests.keys()[0]
        other_request1 = lookup.pending_requests.values()[1]
        other_request2 = lookup.pending_requests.values()[2]
        other_request1.cancel = MagicMock()
        other_request2.cancel = MagicMock()
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Value(uuid, self.node.id, self.key, self.value, self.timestamp,
                    self.expires, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Ensure the lookup has fired.
        self.assertTrue(lookup.called)
        # Check the pending requests have been cancelled.
        self.assertEqual(1, other_request1.cancel.call_count)
        self.assertEqual(1, other_request2.cancel.call_count)
        # Make sure the pending_requests dict is empty.
        self.assertEqual(0, len(lookup.pending_requests))

        # Ensure the result of the callback is the returned Value object.
        def callback(result):
            self.assertEqual(msg, result)
        lookup.addCallback(callback)

    def test_handle_response_value_message_wrong_key(self):
        """
        Ensures that if we get a valid Value response but the key doesn't match
        the one being requested then the misbehaving node is blacklisted and
        an exception is thrown.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindValue, self.node)

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        key = construct_key(PUBLIC_KEY, 'foo')
        signature = generate_signature(self.value, self.timestamp,
                                       self.expires, 'foo', self.meta,
                                       PRIVATE_KEY)
        msg = Value(uuid, self.node.id, key, self.value, self.timestamp,
                    self.expires, PUBLIC_KEY, self.name, self.meta,
                    signature, self.node.version)
        lookup._blacklist = MagicMock()
        ex = self.assertRaises(ValueError, lookup._handle_response, uuid,
                               contact, msg)
        self.assertEqual('Value with wrong key returned by %r' % contact,
                         ex.message)
        lookup._blacklist.assert_called_once_with(contact)

    def test_handle_response_value_message_expired(self):
        """
        Ensures the NodeLookup errbacks given an expired value response.
        """
        def side_effect(*args):
            """
            Ensures the mock returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        lookup = NodeLookup(self.key, FindValue, self.node)

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        timestamp = time.time() - 1000
        expires = timestamp + 10
        signature = generate_signature(self.value, self.timestamp,
                                       self.expires, 'foo', self.meta,
                                       PRIVATE_KEY)
        msg = Value(uuid, self.node.id, self.key, self.value, timestamp,
                    expires, PUBLIC_KEY, self.name, self.meta, signature,
                    self.node.version)
        ex = self.assertRaises(ValueError, lookup._handle_response, uuid,
                               contact, msg)
        self.assertEqual('Expired value returned by %r' % contact,
                         ex.message)

    @patch('drogulus.dht.node.sort_contacts')
    def test_handle_response_nodes_message_adds_to_shortlist(self, mock_sort):
        """
        Ensures that a Nodes message adds the returned nodes to the shortlist
        in the correct order (closest to target at the head of the list).
        """
        def sort_side_effect(*args):
            """
            Ensures the sort algorithm returns some arbitrary value.
            """
            return [1, 2, 3]

        mock_sort.side_effect = sort_side_effect

        def send_file_side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=send_file_side_effect)
        target_key = long_to_hex(999)
        lookup = NodeLookup(target_key, FindNode, self.node)
        shortlist = lookup.shortlist

        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        mock_sort.assert_called_once_with(list(self.nodes) + shortlist,
                                          target_key)
        self.assertEqual([1, 2, 3], lookup.shortlist)

    def test_handle_response_nodes_message_update_nearest_node(self):
        """
        Ensure that if the response contains contacts/nodes that are nearer to
        the target than the current nearest known node nearest_node is updated
        to reflect this change of state.
        """
        def side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        target_key = long_to_hex(999)
        lookup = NodeLookup(target_key, FindNode, self.node)
        old_nearest_node = lookup.nearest_node

        lookup._lookup = MagicMock()
        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Check the nearest_node has been updated to the correct value and that
        # the lookup has been restarted.
        self.assertNotEqual(old_nearest_node, lookup.nearest_node)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])
        self.assertEqual(1, lookup._lookup.call_count)

    def test_handle_response_nodes_message_do_not_update_nearest_node(self):
        """
        If the response contains contacts/nodes that are NOT closer to the
        target than the current nearest known node then nearest_node is NOT
        updated and a new lookup is NOT triggered.
        """
        def side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        target_key = long_to_hex(0)
        lookup = NodeLookup(target_key, FindNode, self.node)
        old_nearest_node = lookup.nearest_node

        lookup._lookup = MagicMock()
        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Check the nearest_node has NOT been updated nor has the lookup been
        # restarted.
        self.assertEqual(old_nearest_node, lookup.nearest_node)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])
        self.assertEqual(0, lookup._lookup.call_count)

    def test_handle_response_still_nodes_uncontacted_in_shortlist(self):
        """
        Ensure that if there are no more pending requests but there are still
        uncontacted nodes in the shortlist then restart the lookup.
        """
        def side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        target_key = long_to_hex(0)
        lookup = NodeLookup(target_key, FindNode, self.node)

        # Only one item in pending_requests.
        pending_keys = lookup.pending_requests.keys()
        for i in range(1, len(lookup.pending_requests)):
            del lookup.pending_requests[pending_keys[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add K-1 items from shortlist to the contacted set.
        for i in range(K - 1):
            lookup.contacted.add(lookup.shortlist[i])
        # Ensure lookup is called with the 20th (uncontacted) contact.
        not_contacted = lookup.shortlist[K - 1]
        self.assertNotIn(not_contacted, lookup.contacted)
        lookup._lookup = MagicMock()
        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Lookup is called once.
        self.assertEqual(1, lookup._lookup.call_count)
        # Lookup results in the expected call with the un-contacted node.
        self.node.send_find.called_once_with(not_contacted, target_key,
                                             FindNode)

    def test_handle_response_all_shortlist_contacted_return_nodes(self):
        """
        Ensure that if there are no more pending requests and all the nodes in
        the shortlist have been contacted then return the shortlist of nearest
        nodes to the target key if the lookup is a FindNode.
        """
        def side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        target_key = long_to_hex(0)
        lookup = NodeLookup(target_key, FindNode, self.node)

        # Only one item in pending_requests.
        pending_keys = lookup.pending_requests.keys()
        for i in range(1, len(lookup.pending_requests)):
            del lookup.pending_requests[pending_keys[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add all items from shortlist to the contacted set.
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        # Cause the callback to fire.
        lookup._lookup = MagicMock()
        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Lookup is not called.
        self.assertEqual(0, lookup._lookup.call_count)
        # The lookup has fired.
        self.assertTrue(lookup.called)

        # The result is the ordered shortlist of contacts closest to the
        # target.
        def handle_callback(result):
            """
            Checks the result is the expected list of contacts.
            """
            # It's a list.
            self.assertIsInstance(result, list)
            # It's the lookup's shortlist.
            self.assertEqual(result, lookup.shortlist)
            # It's in order.
            ordered = sort_contacts(lookup.shortlist, target_key)
            self.assertEqual(ordered, result)

        lookup.addCallback(handle_callback)

    def test_handle_response_all_shortlist_contacted_no_value_found(self):
        """
        Ensure that if there are no more pending requests and all the nodes in
        the shortlist have been contacted yet the target key has not yet been
        found (because it's a FindValue query) then errback with a
        ValueNotFound exception.
        """
        def side_effect(*args):
            """
            Ensures the mock send_file returns something useful.
            """
            uuid = str(uuid4())
            deferred = defer.Deferred()
            return (uuid, deferred)

        self.node.send_find = MagicMock(side_effect=side_effect)
        target_key = long_to_hex(0)
        lookup = NodeLookup(target_key, FindValue, self.node)

        # Only one item in pending_requests.
        pending_keys = lookup.pending_requests.keys()
        for i in range(1, len(lookup.pending_requests)):
            del lookup.pending_requests[pending_keys[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add all items from shortlist to the contacted set.
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        # Cause the callback to fire.
        lookup._lookup = MagicMock()
        uuid = lookup.pending_requests.keys()[0]
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        msg = Nodes(self.uuid, self.node.id, self.nodes, self.node.version)
        lookup._handle_response(uuid, contact, msg)
        # Lookup is not called.
        self.assertEqual(0, lookup._lookup.call_count)
        # The lookup has fired.
        self.assertTrue(lookup.called)

        # The error is a ValueNotFound exception.
        def handle_errback(error):
            """
            Ensures the expected exception is raised.
            """
            self.assertIsInstance(error.value, ValueNotFound)
            self.assertEqual("Unable to find value for key: %r" % target_key,
                             error.getErrorMessage())

        lookup.addErrback(handle_errback)


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
        reactor.callLater = self.clock.callLater
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

    def test_message_received_pong(self):
        """
        Ensures a Pong message is handled correctly.
        """
        self.node.handle_pong = MagicMock()
        # Create a simple Pong message.
        uuid = str(uuid4())
        version = get_version()
        msg = Pong(uuid, self.node_id, version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_pong method.
        self.node.handle_pong.assert_called_once_with(msg)

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

    def test_message_received_value(self):
        """
        Ensures a Value message is handled correctly.
        """
        self.node.handle_value = MagicMock()
        # Create a Value message.
        uuid = str(uuid4())
        msg = Value(uuid, self.node.id, self.key, self.value, self.timestamp,
                    self.expires, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.node.version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '192.168.1.1', 54321, self.version)
        # Check it results in a call to the node's handle_value method.
        self.node.handle_value.assert_called_once_with(msg, contact)

    def test_message_received_nodes(self):
        """
        Ensures a Nodes message is handled correctly.
        """
        self.node.handle_nodes = MagicMock()
        # Create a nodes message.
        msg = Nodes(self.uuid, self.node.id,
                    ((self.node.id, '127.0.0.1', 1908, '0.1')),
                    self.node.version)
        # Receive it...
        self.node.message_received(msg, self.protocol)
        # Check it results in a call to the node's handle_nodes method.
        self.node.handle_nodes.assert_called_once_with(msg)

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

    @patch('drogulus.dht.node.validate_message')
    def test_handle_store_checks_with_validate_message(self, mock_validator):
        """
        Ensure that the validate_message function is called as part of
        handle_store.
        """
        # Mock
        mock_validator.return_value = (1, 2)
        self.protocol.sendMessage = MagicMock()
        # Create a fake contact and valid message.
        msg = Store(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        self.node.handle_store(msg, self.protocol, other_node)
        mock_validator.assert_called_once_with(msg)

    @patch('drogulus.dht.node.reactor.callLater')
    def test_handle_store(self, mock_call_later):
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
        # Ensure call_later has been called to replicate the value.
        mock_call_later.assert_called_once_with(REPLICATE_INTERVAL,
                                                self.node.send_replicate,
                                                msg)
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
            'message': 'You have been blacklisted.'
        }
        self.assertEqual(ex.args[2], details)
        self.assertEqual(ex.args[3], self.uuid)
        # Ensure the message is not in local storage.
        self.assertNotIn(self.key, self.node._data_store)
        # Ensure the contact is not in the routing table
        self.assertEqual(0, len(self.node._routing_table._buckets[0]))
        # Ensure the contact is not in the replacement cache
        self.assertEqual(0, len(self.node._routing_table._replacement_cache))

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
            contact = Contact(2 ** i, "192.168.0.%d" % i, 9999, self.version,
                              0)
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
            contact = Contact(2 ** i, "192.168.0.%d" % i, 9999, self.version,
                              0)
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

    @patch('drogulus.dht.node.validate_message')
    def test_handle_value_checks_with_validate_message(self, mock_validator):
        """
        Ensure that the validate_message function is called as part of
        handle_value.
        """
        mock_validator.return_value = (1, 2)
        # Create a fake contact and valid message.
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        msg = Value(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.node.version)
        # Handle it.
        self.node.handle_value(msg, other_node)
        mock_validator.assert_called_once_with(msg)

    def test_handle_value_with_valid_message(self):
        """
        Ensure a valid Value is checked and results in the expected call to
        trigger_deferred.
        """
        # Mock
        self.node.trigger_deferred = MagicMock()
        # Create a fake contact and valid message.
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        msg = Value(self.uuid, self.node.id, self.key, self.value,
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.node.version)
        # Handle it.
        self.node.handle_value(msg, other_node)
        self.node.trigger_deferred.assert_called_once_with(msg)

    def test_handle_value_with_bad_message(self):
        """
        Ensure a bad message results in an error sent to trigger_deferred along
        with expected logging and removal or the other node from the local
        node's routing table.
        """
        # Mocks
        self.node._routing_table.remove_contact = MagicMock()
        self.node.trigger_deferred = MagicMock()
        patcher = patch('drogulus.dht.node.log.msg')
        mockLog = patcher.start()
        # Create a fake contact and valid message.
        other_node = Contact(self.node.id, '127.0.0.1', 1908,
                             self.version, time.time())
        msg = Value(self.uuid, self.node.id, self.key, 'bad_value',
                    self.timestamp, self.expires, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.node.version)
        # Handle it.
        self.node.handle_value(msg, other_node)
        # Logger was called twice.
        self.assertEqual(2, mockLog.call_count)
        # other node was removed from the routing table.
        self.node._routing_table.remove_contact.\
            assert_called_once_with(other_node.id, True)
        # trigger_deferred called as expected.
        self.assertEqual(1, self.node.trigger_deferred.call_count)
        self.assertEqual(self.node.trigger_deferred.call_args[0][0], msg)
        self.assertIsInstance(self.node.trigger_deferred.call_args[0][1],
                              ValueError)
        # Tidy up.
        patcher.stop()

    def test_handle_nodes(self):
        """
        Ensure a Nodes message merely results in the expected call to
        trigger_deferred.
        """
        self.node.trigger_deferred = MagicMock()
        msg = Nodes(self.uuid, self.node.id,
                    ((self.node.id, '127.0.0.1', 1908, '0.1')),
                    self.node.version)
        self.node.handle_nodes(msg)
        self.node.trigger_deferred.assert_called_once_with(msg)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message(self, mock_client):
        """
        Ensure send_message returns a deferred.
        """
        # Mock, mock, glorious mock; nothing quite like it to test a code
        # block. (To the tune of "Mud, mud, glorious mud!")
        mock_client.return_value = FakeClient(self.protocol)
        # Mock the callLater function
        patcher = patch('drogulus.dht.node.reactor.callLater')
        mockCallLater = patcher.start()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        # Check for the deferred.
        result = self.node.send_message(contact, msg)
        self.assertTrue(isinstance(result, defer.Deferred))
        # Ensure the timeout function was called
        call_count = mockCallLater.call_count
        # Tidy up.
        patcher.stop()
        # Check callLater was called twice - once each for connection timeout
        # and message timeout.
        self.assertEqual(2, call_count)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_on_connect_adds_message_to_pending(self,
                                                             mock_client):
        """
        Ensure that when a connection is made the on_connect function wrapped
        inside send_message adds the message and deferred to the pending
        messages dictionary.
        """
        # Mock.
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
    def test_send_message_timeout_connection_cancel_called(self, mock_client):
        """
        If attempting to connect times out before the connection is eventuially
        made, ensure the connection's deferred is cancelled.
        """
        mock_client.return_value = FakeClient(self.protocol, True, True, True)
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        self.node.send_message(contact, msg)
        self.clock.advance(RPC_TIMEOUT)
        self.assertNotIn(uuid, self.node._pending)
        self.assertEqual(1,
                         mock_client.return_value.cancel_function.call_count)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_timeout_remove_contact(self, mock_client):
        """
        If the connection deferred is cancelled ensure that the node's
        _routing_table.remove_contact is called once.
        """
        mock_client.return_value = FakeClient(self.protocol, True, True, False)
        self.node._routing_table.remove_contact = MagicMock()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        self.node.send_message(contact, msg)
        self.clock.advance(RPC_TIMEOUT)
        self.assertNotIn(uuid, self.node._pending)
        self.node._routing_table.remove_contact.\
            assert_called_once_with(self.node.id)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_response_timeout_call_later(self, mock_client):
        """
        Ensure that when a connection is made the on_connect function wrapped
        inside send_message calls callLater with the response_timeout function.
        """
        mock_client.return_value = FakeClient(self.protocol)
        # Mock the timeout function
        patcher = patch('drogulus.dht.node.response_timeout')
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
        self.clock.advance(RESPONSE_TIMEOUT)
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

    @patch('drogulus.dht.node.clientFromString')
    def test_send_message_fires_errback_in_case_of_errors(self, mock_client):
        """
        Ensure that if there's an error during connection or sending of the
        message then the errback is fired.
        """
        mock_client.return_value = FakeClient(self.protocol, success=False)
        errback = MagicMock()
        patcher = patch('drogulus.dht.node.log.msg')
        mockLog = patcher.start()
        # Create a simple Ping message.
        uuid = str(uuid4())
        version = get_version()
        msg = Ping(uuid, self.node_id, version)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        deferred = self.node.send_message(contact, msg)
        deferred.addErrback(errback)
        # The errback is called and the error is logged automatically.
        self.assertEqual(1, errback.call_count)
        self.assertEqual(2, mockLog.call_count)
        # Tidy up.
        patcher.stop()
        self.clock.advance(RPC_TIMEOUT)

    def test_trigger_deferred_no_match(self):
        """
        Ensures that there are no changes to the _pending dict if there are
        no matches for the incoming message's uuid.
        """
        to_not_match = str(uuid4())
        self.node._pending[to_not_match] = defer.Deferred()
        # Create a simple Pong message.
        uuid = str(uuid4())
        version = get_version()
        msg = Pong(uuid, self.node_id, version)
        # Trigger.
        self.node.trigger_deferred(msg)
        # Check.
        self.assertEqual(1, len(self.node._pending))
        self.assertIn(to_not_match, self.node._pending)

    def test_trigger_deferred_with_error(self):
        """
        Ensures that an errback is called on the correct deferred given the
        incoming message's uuid if the error flag is passed in.
        """
        uuid = str(uuid4())
        deferred = defer.Deferred()
        self.node._pending[uuid] = deferred
        handler = MagicMock()
        deferred.addErrback(handler)
        # Create an Error message.
        version = get_version()
        code = 1
        title = ERRORS[code]
        details = {'foo': 'bar'}
        msg = Error(uuid, self.node_id, code, title, details, version)
        # Sanity check.
        self.assertEqual(1, len(self.node._pending))
        # Trigger.
        error = ValueError('Information about the erroneous message')
        self.node.trigger_deferred(msg, error)
        # The deferred has fired with an errback.
        self.assertTrue(deferred.called)
        self.assertEqual(1, handler.call_count)
        self.assertEqual(handler.call_args[0][0].value, error)
        self.assertEqual(handler.call_args[0][0].value.message, msg)
        self.assertEqual(handler.call_args[0][0].__class__, Failure)

    def test_trigger_deferred_with_ok_message(self):
        """
        Ensures that a callback is triggered on the correct deferred given the
        incoming message's uuid.
        """
        # Set up a simple Pong message.
        uuid = str(uuid4())
        deferred = defer.Deferred()
        self.node._pending[uuid] = deferred
        handler = MagicMock()
        deferred.addCallback(handler)
        version = get_version()
        msg = Pong(uuid, self.node_id, version)
        # Sanity check.
        self.assertEqual(1, len(self.node._pending))
        # Trigger.
        self.node.trigger_deferred(msg)
        # The deferred has fired with a callback.
        self.assertTrue(deferred.called)
        self.assertEqual(1, handler.call_count)
        self.assertEqual(handler.call_args[0][0], msg)
        # The deferred is removed from pending.
        self.assertEqual(0, len(self.node._pending))

    def test_trigger_deferred_cleans_up(self):
        """
        Ensures that once the deferred is triggered it is cleaned from the
        node's _pending dict.
        """
        # Set up a simple Pong message.
        uuid = str(uuid4())
        deferred = defer.Deferred()
        self.node._pending[uuid] = deferred
        handler = MagicMock()
        deferred.addCallback(handler)
        version = get_version()
        msg = Pong(uuid, self.node_id, version)
        # Sanity check.
        self.assertEqual(1, len(self.node._pending))
        # Trigger.
        self.node.trigger_deferred(msg)
        # The deferred is removed from pending.
        self.assertEqual(0, len(self.node._pending))

    def test_handle_pong(self):
        """
        Ensures that a pong message triggers the correct deferred that was
        originally created by an outgoing (ping) message.
        """
        # Mock
        self.node.trigger_deferred = MagicMock()
        # Create a simple Pong message.
        uuid = str(uuid4())
        version = get_version()
        msg = Pong(uuid, self.node_id, version)
        # Handle it.
        self.node.handle_pong(msg)
        # Check the result.
        result = Pong(uuid, self.node.id, version)
        self.node.trigger_deferred.assert_called_once_with(result)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_ping_returns_deferred(self, mock_client):
        """
        Ensures that sending a ping returns a deferred.
        """
        mock_client.return_value = FakeClient(self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        deferred = self.node.send_ping(contact)
        self.assertIsInstance(deferred, defer.Deferred)
        # Tidy up.
        self.clock.advance(RPC_TIMEOUT)

    def test_send_ping_calls_send_message(self):
        """
        Ensures that sending a ping calls the node's send_message method with
        the ping message.
        """
        # Mock
        self.node.send_message = MagicMock()
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        self.node.send_ping(contact)
        self.assertEqual(1, self.node.send_message.call_count)
        called_contact = self.node.send_message.call_args[0][0]
        self.assertEqual(contact, called_contact)
        message_to_send = self.node.send_message.call_args[0][1]
        self.assertIsInstance(message_to_send, Ping)

    @patch('drogulus.dht.node.generate_signature')
    def test_send_store_generates_signature(self, mock):
        """
        Ensure the generate_signature function is called with the expected
        arguments as part of send_store.
        """
        mock.return_value = 'test'
        self.node.send_store(PRIVATE_KEY, PUBLIC_KEY, self.name,
                             self.value, self.timestamp, self.expires,
                             self.meta)
        mock.assert_called_once_with(self.value, self.timestamp, self.expires,
                                     self.name, self.meta, PRIVATE_KEY)

    @patch('drogulus.dht.node.construct_key')
    def test_send_store_makes_compound_key(self, mock):
        """
        Ensure the construct_key function is called with the expected arguments
        as part of send_store.
        """
        mock.return_value = 'test'
        self.node.send_store(PRIVATE_KEY, PUBLIC_KEY, self.name,
                             self.value, self.timestamp, self.expires,
                             self.meta)
        mock.assert_called_once_with(PUBLIC_KEY, self.name)

    def test_send_store_calls_send_replicate(self):
        """
        Ensure send_replicate is called as part of send_store.
        """
        self.node.send_replicate = MagicMock()
        self.node.send_store(PRIVATE_KEY, PUBLIC_KEY, self.name,
                             self.value, self.timestamp, self.expires,
                             self.meta)
        self.assertEqual(1, self.node.send_replicate.call_count)

    def test_send_store_creates_expected_store_message(self):
        """
        Ensure the message passed in to send_replicate looks correct.
        """
        self.node.send_replicate = MagicMock()
        self.node.send_store(PRIVATE_KEY, PUBLIC_KEY, self.name,
                             self.value, self.timestamp, self.expires,
                             self.meta)
        self.assertEqual(1, self.node.send_replicate.call_count)
        message_to_send = self.node.send_replicate.call_args[0][0]
        self.assertIsInstance(message_to_send, Store)
        self.assertTrue(message_to_send.uuid)
        self.assertEqual(message_to_send.node, self.node.id)
        self.assertEqual(message_to_send.key, self.key)
        self.assertEqual(message_to_send.value, self.value)
        self.assertEqual(message_to_send.timestamp, self.timestamp)
        self.assertEqual(message_to_send.expires, self.expires)
        self.assertEqual(message_to_send.public_key, PUBLIC_KEY)
        self.assertEqual(message_to_send.name, self.name)
        self.assertEqual(message_to_send.meta, self.meta)
        self.assertEqual(message_to_send.sig, self.signature)
        self.assertEqual(message_to_send.version, self.node.version)

    @patch('drogulus.dht.node.clientFromString')
    def test_send_find_returns_uuid_and_deferred(self, mock_client):
        """
        Ensures that sending a Find[Node|Value] message returns a deferred.
        """
        mock_client.return_value = FakeClient(self.protocol)
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        target = '123456'
        find_class = FindNode
        uuid, deferred = self.node.send_find(contact, target, find_class)
        self.assertIsInstance(uuid, str)
        self.assertIsInstance(deferred, defer.Deferred)
        # Tidy up.
        self.clock.advance(RPC_TIMEOUT)

    def test_send_find_as_findnode_calls_send_message(self):
        """
        Ensures that sending a FindNode message causes the node's send_message
        method to be called with the expected message.
        """
        # Mock
        self.node.send_message = MagicMock()
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        target = '123456'
        find_class = FindNode
        uuid, deferred = self.node.send_find(contact, target, find_class)
        self.assertEqual(1, self.node.send_message.call_count)
        called_contact = self.node.send_message.call_args[0][0]
        self.assertEqual(contact, called_contact)
        message_to_send = self.node.send_message.call_args[0][1]
        self.assertIsInstance(message_to_send, FindNode)
        self.assertEqual(target, message_to_send.key)

    def test_send_find_as_findvalue_calls_send_message(self):
        """
        Ensures that sending a FindValue message causes the node's send_message
        method to be called with the expected message.
        """
        # Mock
        self.node.send_message = MagicMock()
        # Dummy contact.
        contact = Contact(self.node.id, '127.0.0.1', 54321, self.version)
        target = '123456'
        find_class = FindValue
        uuid, deferred = self.node.send_find(contact, target, find_class)
        self.assertEqual(1, self.node.send_message.call_count)
        called_contact = self.node.send_message.call_args[0][0]
        self.assertEqual(contact, called_contact)
        message_to_send = self.node.send_message.call_args[0][1]
        self.assertIsInstance(message_to_send, FindValue)
        self.assertEqual(target, message_to_send.key)
