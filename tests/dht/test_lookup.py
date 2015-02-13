# -*- coding: utf-8 -*-
"""
Ensures the Lookup classes work as expected.
"""
from drogulus.dht.lookup import Lookup
from drogulus.dht.contact import PeerNode
from drogulus.dht.node import Node
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.messages import FindNode, Nodes, FindValue, Value, OK
from drogulus.dht.errors import RoutingTableEmpty
from drogulus.dht.constants import LOOKUP_TIMEOUT, K, ALPHA
from drogulus.dht.utils import sort_peer_nodes
from drogulus.dht.errors import ValueNotFound
from drogulus.dht.utils import distance
from drogulus.version import get_version
from .keys import PRIVATE_KEY, PUBLIC_KEY
from hashlib import sha512
from unittest import mock
import uuid
import asyncio
import unittest
import time


# Create a tuple containing source values ordered by associated sha512 has
# values. These are to be used in place of public_key values to help test
# remote nodes reported back to the Lookup instance.
HASH_TUPLES = []
for i in range(2000):
    s = str(i)
    h = sha512(s.encode('utf-8')).hexdigest()
    HASH_TUPLES.append((s, h))
ORDERED_HASHES = tuple([val[0] for val in
                       sorted(HASH_TUPLES,
                       key=lambda x: distance('0', x[1]))])
TARGET = sha512(ORDERED_HASHES[1000].encode('utf-8')).hexdigest()
CLOSEST_TO_TARGET = tuple([val[0] for val in
                          sorted(HASH_TUPLES,
                          key=lambda x: distance(TARGET, x[1]))])


@asyncio.coroutine
def blip(wait=0.01):
    """
    A coroutine that ends after some period of time to allow tasks scheduled
    in the tests to run.

    THIS IS A QUICK HACK AND SHOULD BE CHANGED TO SOMETHING MORE ELEGANT.
    """
    yield from asyncio.sleep(wait)
    return True


class TestLookup(unittest.TestCase):
    """
    Ensures the Lookup class works as expected.
    """

    def setUp(self):
        """
        Common vars.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        self.version = get_version()
        self.sender = mock.MagicMock()
        self.reply_port = 1908
        self.node = Node(PUBLIC_KEY, PRIVATE_KEY, self.event_loop,
                         self.sender, self.reply_port)
        self.target = TARGET
        self.seal = 'afakesealthatwillnotverify'
        node_list = []
        remote_node_list = []
        for i in range(100, 120):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(ORDERED_HASHES[i], self.version, uri, 0)
            node_list.append(contact)
            remote_node_list.append((ORDERED_HASHES[i], self.version, uri))

        self.nodes = tuple(sort_peer_nodes(node_list, self.target))
        self.remote_nodes = tuple(remote_node_list)

        def side_effect(*args, **kwargs):
            return (str(uuid.uuid4()), asyncio.Future())
        self.node.send_find = mock.MagicMock(side_effect=side_effect)
        self.contacts = []
        node_list = []
        for i in range(20):
            uri = 'netstring://192.168.0.%d:%d/' % (i, self.reply_port)
            contact = PeerNode(ORDERED_HASHES[i], self.version, uri, 0)
            self.node.routing_table.add_contact(contact)
            self.contacts.append((ORDERED_HASHES[i], self.version, uri))

    def test_init(self):
        """
        Ensure instantiating the Lookup class creates an object with the
        expected state.
        """
        patcher = mock.patch('asyncio.base_events.BaseEventLoop.call_later')
        mock_call_later = patcher.start()
        self.node.routing_table.touch_bucket = mock.MagicMock()
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        self.assertIsInstance(lookup, asyncio.Future)
        self.assertEqual(lookup.message_type, FindNode)
        self.assertEqual(lookup.target, self.target)
        self.assertEqual(lookup.local_node, self.node)
        self.assertEqual(lookup.event_loop, self.event_loop)
        self.assertIsInstance(lookup.contacted, set)
        self.assertEqual(3, len(lookup.contacted))
        self.assertIsInstance(lookup.pending_requests, dict)
        self.assertEqual(3, len(lookup.pending_requests))
        mock_call_later.assert_called_once_with(LOOKUP_TIMEOUT,
                                                lookup.cancel)
        self.assertEqual(len(lookup.shortlist), len(self.contacts))
        self.node.routing_table.touch_bucket.\
            assert_called_once_with(self.target)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])
        self.assertEqual(3, self.node.send_find.call_count)
        patcher.stop()

    def test_init_no_shortlist(self):
        """
        Ensure the Future is marked as done with a RoutingTableEmpty exception.
        """
        # Create an empty routing table.
        self.node.routing_table = RoutingTable(self.node.network_id)
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        self.assertEqual(True, lookup.done())
        self.assertRaises(RoutingTableEmpty, lookup.result)

    def test_init_skips_touch_bucket_if_local_network_id_is_key(self):
        """
        Ensure touch_bucket doesn't happen if the target key is the local
        node's network_id.
        """
        self.node.routing_table.touch_bucket = mock.MagicMock()
        Lookup(FindNode, self.node.network_id, self.node, self.event_loop)
        self.assertEqual(self.node.routing_table.touch_bucket.call_count, 0)

    def test_cancel_pending_requests(self):
        """
        Ensure all the tasks in the lookup's pending_requests dict are
        cancelled.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        # Sanity check
        self.assertEqual(3, len(lookup.pending_requests))
        tasks = lookup.pending_requests.values()
        lookup._cancel_pending_requests()
        self.event_loop.run_until_complete(blip())
        self.assertEqual(lookup.pending_requests, {})
        for task in tasks:
            self.assertTrue(task.cancelled())

    def test_cancel(self):
        """
        Ensure that the expected operations happen when the lookup's cancel
        method is called (the pending requests also need to be cancelled).
        """
        patcher = mock.patch('asyncio.Future.cancel')
        mock_cancel = patcher.start()
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        lookup._cancel_pending_requests = mock.MagicMock()
        result = lookup.cancel()
        self.assertTrue(result)
        self.assertEqual(lookup._cancel_pending_requests.call_count, 1)
        self.assertEqual(mock_cancel.call_count, 1)
        patcher.stop()

    def test_cancel_already_done(self):
        """
        If the lookup is already done, ensure a call to cancel returns the
        expected (False) result.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        lookup.set_result('foo')
        result = lookup.cancel()
        self.assertFalse(result)

    def test_handle_error(self):
        """
        The _handle_error method cleanly deals with the fallout of
        encountering an error generated from an interaction with a peer node.
        """
        patcher = mock.patch('drogulus.dht.lookup.log.info')
        mock_info = patcher.start()
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        uuid = [uuid for uuid in lookup.pending_requests.keys()][0]
        pending_task = lookup.pending_requests[uuid]
        contact = lookup.shortlist[0]
        lookup._handle_error(uuid, contact, Exception('Foo'))
        self.assertNotIn(contact, lookup.shortlist)
        self.assertNotIn(uuid, lookup.pending_requests)
        self.assertTrue(pending_task.cancelled())
        # Log the error and associated exception (2 calls)
        self.assertEqual(mock_info.call_count, 2)
        self.assertEqual(lookup._lookup.call_count, 1)
        patcher.stop()

    def test_blacklist(self):
        """
        Ensure a blacklist operation (where misbehaving peer nodes are marked
        as to be ignored) works as expected.
        """
        self.node.routing_table.blacklist = mock.MagicMock()
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        contact = lookup.shortlist[0]
        lookup._blacklist(contact)
        self.assertNotIn(contact, lookup.shortlist)
        self.node.routing_table.blacklist.assert_called_once_with(contact)

    def test_handle_response_wrong_message_type(self):
        """
        Ensure that a response that isn't a Nodes or Value message results in
        the responding peer node being blacklisted and the error being
        correctly handled.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        uuid = [uuid for uuid in lookup.pending_requests.keys()][0]
        contact = lookup.shortlist[0]
        msg = OK(uuid, self.node.network_id, self.node.network_id,
                 self.reply_port, self.version, self.seal)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._blacklist = mock.MagicMock()
        lookup._handle_error = mock.MagicMock()
        lookup._handle_response(uuid, contact, response)
        lookup._blacklist.assert_called_once_with(contact)
        self.assertEqual(lookup._handle_error.call_count, 1)
        args = lookup._handle_error.call_args[0]
        self.assertEqual(args[0], uuid)
        self.assertEqual(args[1], contact)
        self.assertIsInstance(args[2], TypeError)
        self.assertEqual(args[2].args[0],
                         "Unexpected response type from {}".format(contact))

    def test_handle_response_wrong_value_for_findnode_message(self):
        """
        Ensures that if a Value message is returned for a FindNode request
        then the misbehaving peer is blacklisted and the error is handled
        correctly.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        uuid = [uuid for uuid in lookup.pending_requests.keys()][0]
        contact = lookup.shortlist[0]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, self.target,
                    'value', time.time(), time.time() + 99999, self.version,
                    PUBLIC_KEY, 'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._blacklist = mock.MagicMock()
        lookup._handle_error = mock.MagicMock()
        lookup._handle_response(uuid, contact, response)
        lookup._blacklist.assert_called_once_with(contact)
        self.assertEqual(lookup._handle_error.call_count, 1)
        args = lookup._handle_error.call_args[0]
        self.assertEqual(args[0], uuid)
        self.assertEqual(args[1], contact)
        self.assertIsInstance(args[2], TypeError)
        self.assertEqual(args[2].args[0],
                         "Unexpected response type from {}".format(contact))

    def test_handle_response_remove_request_from_pending(self):
        """
        Ensure the pending request that triggered the response being handled
        by the _handle_response callback is removed from the pending_requests
        dict.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        uuid = [uuid for uuid in lookup.pending_requests.keys()][0]
        contact = lookup.shortlist[0]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, self.target,
                    'value', time.time(), time.time() + 99999, self.version,
                    PUBLIC_KEY, 'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertNotIn(uuid, lookup.pending_requests.keys())

    def test_handle_response_value_results_in_node_lookup_callback(self):
        """
        Tests that if a valid Value message is handled then all the other
        pending requests for the lookup are cancelled and the lookup has its
        set_result method called with the Value.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        other_request1 = lookup.pending_requests[uuids[1]]
        other_request2 = lookup.pending_requests[uuids[2]]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, self.target,
                    'value', time.time(), time.time() + 99999, self.version,
                    PUBLIC_KEY, 'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.event_loop.run_until_complete(blip())
        # Check the lookup has fired correctly.
        self.assertTrue(lookup.done())
        self.assertEqual(lookup.result(), msg)
        # Check the other requests are cancelled.
        self.assertTrue(other_request1.cancelled())
        self.assertTrue(other_request2.cancelled())
        # Make sure the pending_requests dict is empty.
        self.assertEqual(0, len(lookup.pending_requests))
        # Ensure the contact that provided the result is NOT in the shortlist.
        self.assertNotIn(contact, lookup.shortlist)

    def test_handle_response_value_message_wrong_key(self):
        """
        If a valid Value response is received but the key doesn't match the
        one being requested then the misbehaving node is blacklisted and
        appropriately dealt with.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, 'f00baa',
                    'value', time.time(), time.time() + 99999, self.version,
                    PUBLIC_KEY, 'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._blacklist = mock.MagicMock()
        lookup._handle_error = mock.MagicMock()
        lookup._handle_response(uuid, contact, response)
        lookup._blacklist.assert_called_once_with(contact)
        self.assertEqual(lookup._handle_error.call_count, 1)
        args = lookup._handle_error.call_args[0]
        self.assertEqual(args[0], uuid)
        self.assertEqual(args[1], contact)
        self.assertIsInstance(args[2], ValueError)
        self.assertEqual(args[2].args[0],
                         "Value with wrong key returned by {}"
                         .format(contact))

    def test_handle_response_value_expired(self):
        """
        Ensures an expired Value is handled correctly.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, self.target,
                    'value', time.time(), time.time() - 99999, self.version,
                    PUBLIC_KEY, 'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_error = mock.MagicMock()
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup._handle_error.call_count, 1)
        args = lookup._handle_error.call_args[0]
        self.assertEqual(args[0], uuid)
        self.assertEqual(args[1], contact)
        self.assertIsInstance(args[2], ValueError)
        self.assertEqual(args[2].args[0],
                         "Expired value returned by {}".format(contact))

    def test_handle_response_value_never_expires(self):
        """
        Ensures an expired Value is handled correctly.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        msg = Value(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, self.target,
                    'value', time.time(), 0.0, self.version, PUBLIC_KEY,
                    'name', 'signature')
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup.result(), msg)

    def test_handle_response_nodes_adds_closest_nodes_to_shortlist(self):
        """
        Ensures a Nodes message causes the referenced peer nodes to be added
        to the shortlist in the correct order (closest to the target at the
        head of the list).
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal,
                    self.remote_nodes)
        response = asyncio.Future()
        response.set_result(msg)
        self.assertNotEqual(lookup.shortlist, list(self.nodes))
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup.shortlist, list(self.nodes))

    def test_handle_response_nodes_no_duplicates_in_shortlist(self):
        """
        If the response contains peer nodes that are already found in the
        lookup's shortlist they are not duplicated.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        shortlist = tuple([(p.public_key, p.version, p.uri) for p
                           in lookup.shortlist])
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, shortlist)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup.shortlist, [PeerNode(*n) for n in shortlist])

    def test_handle_response_nodes_update_nearest_node(self):
        """
        If the response contains peer nodes that are nearer to the target then
        the nearest_node variable is updated to reflect this change of state
        and a new lookup call is kicked off.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        old_nearest_node = lookup.nearest_node
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal,
                    self.remote_nodes)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertNotEqual(lookup.nearest_node, old_nearest_node)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])
        self.assertEqual(lookup._lookup.call_count, 1)

    def test_handle_response_nodes_do_not_update_nearest_node(self):
        """
        If the response contains peer nodes that are NOT closer to the target
        than the current nearest known node then nearest_node is NOT
        updated and a new lookup is NOT triggered.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        old_nearest_node = lookup.nearest_node
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        shortlist = tuple([(p.public_key, p.version, p.uri) for p
                           in lookup.shortlist])
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal, shortlist)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup.nearest_node, old_nearest_node)
        self.assertEqual(lookup.nearest_node, lookup.shortlist[0])
        self.assertEqual(lookup._lookup.call_count, 0)

    def test_handle_response_still_nodes_uncontacted_in_shortlist(self):
        """
        Ensure that if there are no more pending requests but there are still
        uncontacted nodes in the shortlist then restart the lookup.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        # Only one item in pending_requests
        for i in range(1, len(uuids)):
            del lookup.pending_requests[uuids[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add K-1 items from shortlist to the contacted set.
        for i in range(K - 1):
            lookup.contacted.add(lookup.shortlist[i])
        # Ensure lookup is called with the 20th (uncontacted) contact.
        not_contacted = lookup.shortlist[K - 1]
        self.assertNotIn(not_contacted, lookup.contacted)
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal,
                    self.contacts)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        self.assertEqual(lookup._lookup.call_count, 1)
        self.node.send_find.called_once_with(not_contacted, self.target,
                                             FindNode)

    def test_handle_response_all_shortlist_contacted_return_nodes(self):
        """
        If there are no more pending requests and all the nodes in the
        shortlist have been contacted then return the shortlist of nearest
        peer nodes to the target if the lookup is a FindNode.
        """
        lookup = Lookup(FindNode, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        # Only one item in pending_requests
        for i in range(1, len(uuids)):
            del lookup.pending_requests[uuids[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add K items from shortlist to the contacted set.
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        # Cause the lookup to fire.
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal,
                    self.contacts)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        # The _lookup method should not be called.
        self.assertEqual(lookup._lookup.call_count, 0)
        # The lookup task has fired.
        self.assertTrue(lookup.done())
        # Check the result is the ordered shortlist of contacts that are
        # closest to the target.
        # It should be a list...
        self.assertIsInstance(lookup.result(), list)
        # It should be a list that's the lookup's shortlist...
        self.assertEqual(lookup.result(), lookup.shortlist)
        # It should be a list that's the lookup's shortlist in order.
        ordered = sort_peer_nodes(lookup.shortlist, self.target)
        self.assertEqual(lookup.result(), ordered)

    def test_handle_response_all_shortlist_contacted_value_not_found(self):
        """
        If there are no more pending requests and all the nodes in the
        shortlist have been contacted then return the shortlist of nearest
        peer nodes to the target if the lookup is a FindNode.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        lookup._lookup = mock.MagicMock()
        uuids = [uuid for uuid in lookup.pending_requests.keys()]
        uuid = uuids[0]
        contact = lookup.shortlist[0]
        # Only one item in pending_requests
        for i in range(1, len(uuids)):
            del lookup.pending_requests[uuids[i]]
        self.assertEqual(1, len(lookup.pending_requests))
        # Add K items from shortlist to the contacted set.
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        # Cause the lookup to fire.
        msg = Nodes(uuid, self.node.network_id, self.node.network_id,
                    self.reply_port, self.version, self.seal,
                    self.contacts)
        response = asyncio.Future()
        response.set_result(msg)
        lookup._handle_response(uuid, contact, response)
        # The _lookup method should not be called.
        self.assertEqual(lookup._lookup.call_count, 0)
        # The lookup task has fired.
        self.assertTrue(lookup.done())
        with self.assertRaises(ValueNotFound) as result:
            lookup.result()
        self.assertIsInstance(result.exception, ValueNotFound)
        self.assertEqual(result.exception.args[0],
                         "Unable to find value for key: {}"
                         .format(self.target))

    def test_lookup_none_pending_none_contacted(self):
        """
        Ensure the _lookup method works with no pending requests nor any nodes
        previously contacted (i.e. from a clean state).
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        # The _lookup method is called by __init__.
        # No more than ALPHA requests should be made.
        self.assertEqual(self.node.send_find.call_count, ALPHA)
        # Associated ALPHA number of pending_requests.
        self.assertEqual(len(lookup.pending_requests), ALPHA)
        # Associated contacts in the "contacted" set.
        self.assertEqual(len(lookup.contacted), ALPHA)

    def test_lookup_some_pending_some_contacted(self):
        """
        Ensures the _lookup method works with some pending slots available and
        some nodes previously contacted.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        # Reset in order to manually create the correct state.
        lookup.pending_requests = {}
        lookup.contacted = set()
        self.node.send_find.call_count = 0

        # Add a single pending request.
        pending_uuid = str(uuid.uuid4())
        pending_future = asyncio.Future()
        lookup.pending_requests[pending_uuid] = pending_future
        # Add a single contact to the contacted list.
        lookup.contacted.add(lookup.shortlist[0])
        # Sanity check.
        self.assertEqual(1, len(lookup.pending_requests))
        self.assertEqual(1, len(lookup.contacted))
        # Re-run _lookup and check state has been correctly updated.
        lookup._lookup()
        self.assertEqual(ALPHA - 1, self.node.send_find.call_count)
        self.assertEqual(ALPHA, len(lookup.pending_requests))
        self.assertEqual(ALPHA, len(lookup.contacted))

    def test_lookup_all_pending(self):
        """
        If no more pending slots are available ensure no further network calls
        are made.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        # Sanity check that ALPHA slots are full.
        self.assertEqual(self.node.send_find.call_count, ALPHA)
        self.assertEqual(len(lookup.pending_requests), ALPHA)
        self.assertEqual(len(lookup.contacted), ALPHA)
        self.assertEqual(len(lookup.shortlist), K)
        # Re-run _lookup and ensure no further network calls have been made.
        lookup._lookup()
        self.assertEqual(self.node.send_find.call_count, ALPHA)

    def test_lookup_none_pending_all_contacted(self):
        """
        Ensures the _lookup method works with no pending requests and all known
        peer nodes having been contacted.
        """
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        # Put the lookup object in the state to test.
        lookup.pending_requests = {}
        for contact in lookup.shortlist:
            lookup.contacted.add(contact)
        self.node.send_find.call_count = 0
        # Re-run _lookup and test
        lookup._lookup()
        self.assertEqual(self.node.send_find.call_count, 0)

    def test_lookup_adds_callback(self):
        """
        Ensure the _lookup method add the expected callback to the Future that
        represents the request to the remote node in the DHT.
        """
        # Reset event_loop so we start in a clean state.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        lookup._handle_response = mock.MagicMock()
        keys = []
        for k, v in lookup.pending_requests.items():
            keys.append(k)
            v.set_result('foo')
            self.event_loop.run_until_complete(v)
        self.assertEqual(lookup._handle_response.call_count, 3)
        for i, key in enumerate(keys):
            # check the callback called _handle_response with the correct
            # arguments.
            arg_key = lookup._handle_response.call_args_list[i][0][0]
            self.assertEqual(arg_key, key)
            arg_contact = lookup._handle_response.call_args_list[i][0][1]
            self.assertIn(arg_contact, lookup.contacted)
            arg_future = lookup._handle_response.call_args_list[i][0][2]
            self.assertEqual(arg_future.result(), 'foo')

    def test_lookup_added_callbacks_work_when_cancelled(self):
        """
        Ensures that the callback added to pending requests by the _lookup
        method handles cancelled results. This may happen if the lookup is
        finished because a suitable value has been found (so everything else
        can be stopped ASAP).
        """
        # Reset event_loop so we start in a clean state.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = asyncio.get_event_loop()
        lookup = Lookup(FindValue, self.target, self.node, self.event_loop)
        lookup._handle_response = mock.MagicMock()
        lookup._cancel_pending_requests()
        for k, v in lookup.pending_requests.items():
            v.set_result('foo')
            self.event_loop.run_until_complete(v)
        self.assertEqual(lookup._handle_response.call_count, 0)
