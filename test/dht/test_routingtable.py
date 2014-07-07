# -*- coding: utf-8 -*-
"""
Ensures the routing table (a binary tree used to link buckets with key ranges
in the DHT) works as expected.
"""
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.contact import PeerNode
from drogulus.dht.bucket import Bucket
from drogulus.dht.utils import distance
from drogulus.dht import constants
from drogulus.version import get_version
import unittest
import time
from mock import MagicMock
from .keys import PUBLIC_KEY


class TestRoutingTable(unittest.TestCase):
    """
    Ensures the RoutingTable class works as expected.
    """

    def setUp(self):
        """
        Common vars.
        """
        self.version = get_version()

    def test_init(self):
        """
        Ensures an object is created as expected.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Ensure the initial bucket is created.
        self.assertEqual(1, len(r._buckets))
        # Ensure the parent's node ID is stored.
        self.assertEqual(parent_node_id, r._parent_node_id)

    def test_bucket_index_single_bucket(self):
        """
        Ensures the expected index is returned when only a single bucket
        exists.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # a simple test with only one bucket in the routing table.
        test_key = 'abc123'
        expected_index = 0
        actual_index = r._bucket_index(test_key)
        self.assertEqual(expected_index, actual_index)

    def test_bucket_index_multiple_buckets(self):
        """
        Ensures the expected index is returned when multiple buckets exist.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        r._split_bucket(0)
        split_point = int((2 ** 512) / 2)
        lower_key = hex(split_point - 1)[2:]
        higher_key = hex(split_point + 1)[2:]
        expected_lower_index = 0
        expected_higher_index = 1
        actual_lower_index = r._bucket_index(lower_key)
        actual_higher_index = r._bucket_index(higher_key)
        self.assertEqual(expected_lower_index, actual_lower_index)
        self.assertEqual(expected_higher_index, actual_higher_index)

    def test_bucket_index_as_string_and_int(self):
        """
        Ensures that the specified key can be expressed as both a string
        and integer value.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # key as a string
        test_key = 'abc123'
        expected_index = 0
        actual_index = r._bucket_index(test_key)
        self.assertEqual(expected_index, actual_index)
        # key as an integer
        test_key = '1234567'
        actual_index = r._bucket_index(test_key)
        self.assertEqual(expected_index, actual_index)

    def test_bucket_index_out_of_range(self):
        """
        If the requested id is not within the range of the keyspace then a
        ValueError should be raised.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Populate the routing table with contacts.
        for i in range(512):
            uri = 'netstring://192.168.0.%d:9999/'
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            r.add_contact(contact)
        with self.assertRaises(ValueError):
            # Incoming id that's too small.
            r.find_close_nodes('-1')
        with self.assertRaises(ValueError):
            # Incoming id that's too big
            big_id = hex(2 ** 512)[2:]
            r.find_close_nodes(big_id)

    def test_random_key_in_bucket_range(self):
        """
        Ensures the returned key is within the expected bucket range.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket = Bucket(1, 2)
        r._buckets[0] = bucket
        expected = 1
        actual = int(r._random_key_in_bucket_range(0), 0)
        self.assertEqual(expected, actual)

    def test_split_bucket(self):
        """
        Ensures that the correct bucket is split in two and that the contacts
        are found in the right place.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket = Bucket(0, 100)
        contact1 = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        contact1.network_id = hex(20)
        bucket.add_contact(contact1)
        contact2 = PeerNode(PUBLIC_KEY, '192.168.0.2', 8888, 0)
        contact2.network_id = hex(40)
        bucket.add_contact(contact2)
        contact3 = PeerNode(PUBLIC_KEY, '192.168.0.3', 8888, 0)
        contact3.network_id = hex(60)
        bucket.add_contact(contact3)
        contact4 = PeerNode(PUBLIC_KEY, '192.168.0.4', 8888, 0)
        contact4.network_id = hex(80)
        bucket.add_contact(contact4)
        r._buckets[0] = bucket
        # Sanity check
        self.assertEqual(1, len(r._buckets))
        r._split_bucket(0)
        # Two buckets!
        self.assertEqual(2, len(r._buckets))
        bucket1 = r._buckets[0]
        bucket2 = r._buckets[1]
        # Ensure the right number of contacts are in each bucket in the correct
        # order (most recently added at the head of the list).
        self.assertEqual(2, len(bucket1._contacts))
        self.assertEqual(2, len(bucket2._contacts))
        self.assertEqual(contact1, bucket1._contacts[0])
        self.assertEqual(contact2, bucket1._contacts[1])
        self.assertEqual(contact3, bucket2._contacts[0])
        self.assertEqual(contact4, bucket2._contacts[1])
        # Split the new bucket again, ensuring that only the target bucket is
        # modified.
        r._split_bucket(1)
        self.assertEqual(3, len(r._buckets))
        bucket3 = r._buckets[2]
        # bucket1 remains un-changed
        self.assertEqual(2, len(bucket1._contacts))
        # bucket2 only contains the lower half of its original contacts.
        self.assertEqual(1, len(bucket2._contacts))
        self.assertEqual(contact3, bucket2._contacts[0])
        # bucket3 now contains the upper half of the original contacts.
        self.assertEqual(1, len(bucket3._contacts))
        self.assertEqual(contact4, bucket3._contacts[0])
        # Split the bucket at position 0 and ensure the resulting buckets are
        # in the correct position with the correct content.
        r._split_bucket(0)
        self.assertEqual(4, len(r._buckets))
        bucket1, bucket2, bucket3, bucket4 = r._buckets
        self.assertEqual(1, len(bucket1._contacts))
        self.assertEqual(contact1, bucket1._contacts[0])
        self.assertEqual(1, len(bucket2._contacts))
        self.assertEqual(contact2, bucket2._contacts[0])
        self.assertEqual(1, len(bucket3._contacts))
        self.assertEqual(contact3, bucket3._contacts[0])
        self.assertEqual(1, len(bucket4._contacts))
        self.assertEqual(contact4, bucket4._contacts[0])

    def test_split_bucket_cache_update(self):
        """
        Ensures that if there are cached contacts for the split bucket then
        the two new buckets are topped up, the old cache is removed and two
        new caches created (one for each of the new buckets).
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket = Bucket(0, 100)
        contact1 = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        contact1.network_id = hex(20)
        bucket.add_contact(contact1)
        contact2 = PeerNode(PUBLIC_KEY, '192.168.0.2', 8888, 0)
        contact2.network_id = hex(40)
        bucket.add_contact(contact2)
        contact3 = PeerNode(PUBLIC_KEY, '192.168.0.3', 8888, 0)
        contact3.network_id = hex(60)
        bucket.add_contact(contact3)
        contact4 = PeerNode(PUBLIC_KEY, '192.168.0.4', 8888, 0)
        contact4.network_id = hex(80)
        bucket.add_contact(contact4)
        r._buckets[0] = bucket
        # Add two items to the cache.
        cache = []
        cache_contact1 = PeerNode(PUBLIC_KEY, '192.168.0.5', 8888, 0)
        cache_contact1.network_id = hex(10)
        cache.append(cache_contact1)
        cache_contact2 = PeerNode(PUBLIC_KEY, '192.168.0.6', 8888, 0)
        cache_contact2.network_id = hex(70)
        cache.append(cache_contact2)
        r._replacement_cache = {
            (0, 100): cache
        }
        # Two buckets!
        r._split_bucket(0)
        self.assertEqual(2, len(r._buckets))
        bucket1 = r._buckets[0]
        bucket2 = r._buckets[1]
        # Ensure the right number of contacts are in each bucket in the correct
        # order (most recently added at the head of the list).
        self.assertEqual(3, len(bucket1._contacts))
        self.assertEqual(3, len(bucket2._contacts))
        self.assertEqual(contact1, bucket1._contacts[0])
        self.assertEqual(contact2, bucket1._contacts[1])
        self.assertEqual(cache_contact1, bucket1._contacts[2])
        self.assertEqual(contact3, bucket2._contacts[0])
        self.assertEqual(contact4, bucket2._contacts[1])
        self.assertEqual(cache_contact2, bucket2._contacts[2])
        # Ensure the _replacement_cache is in the expected state.
        self.assertEqual(2, len(r._replacement_cache))
        self.assertNotIn((0, 100), r._replacement_cache)
        self.assertIn((0, 50), r._replacement_cache)
        self.assertIn((50, 100), r._replacement_cache)

    def test_split_bucket_cache_too_full(self):
        """
        If the split occurs and there are too many contacts and cached
        contacts for a new bucket, the remainder or cached contacts are added
        to the cache for the new bucket.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket = Bucket(0, 100)
        low_contacts = []
        high_contacts = []
        for i in range(10):
            contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
            contact.network_id = hex(i)
            bucket.add_contact(contact)
            low_contacts.append(contact)
        for i in range(50, 60):
            contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
            contact.network_id = hex(i)
            bucket.add_contact(contact)
            high_contacts.append(contact)
        r._buckets[0] = bucket
        # Add items to the cache.
        cache = []
        low_cache = []
        high_cache = []
        for i in range(10, 30):
            contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
            contact.network_id = hex(i)
            cache.append(contact)
            low_cache.append(contact)
        for i in range(60, 80):
            contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
            contact.network_id = hex(i)
            cache.append(contact)
            high_cache.append(contact)
        r._replacement_cache = {
            (0, 100): cache
        }
        # Two buckets!
        r._split_bucket(0)
        self.assertEqual(2, len(r._buckets))
        bucket1 = r._buckets[0]
        bucket2 = r._buckets[1]
        # Ensure the right number of contacts are in each bucket in the correct
        # order (most recently added at the head of the list).
        self.assertEqual(20, len(bucket1._contacts))
        self.assertEqual(20, len(bucket2._contacts))
        for i in range(10):
            self.assertEqual(low_contacts[i], bucket1._contacts[i])
            self.assertEqual(low_cache[i], bucket1._contacts[i + 10])
        for i in range(10):
            self.assertEqual(high_contacts[i], bucket2._contacts[i])
            self.assertEqual(high_cache[i], bucket2._contacts[i + 10])
        # Ensure the _replacement_cache is in the expected state.
        self.assertEqual(2, len(r._replacement_cache))
        self.assertNotIn((0, 100), r._replacement_cache)
        self.assertIn((0, 50), r._replacement_cache)
        self.assertIn((50, 100), r._replacement_cache)
        self.assertEqual(10, len(r._replacement_cache[(0, 50)]))
        self.assertEqual(10, len(r._replacement_cache[(50, 100)]))
        for i in range(10):
            self.assertEqual(low_cache[i + 10],
                             r._replacement_cache[(0, 50)][i])
            self.assertEqual(high_cache[i + 10],
                             r._replacement_cache[(50, 100)][i])

    def test_blacklist(self):
        """
        Ensures a misbehaving peer is correctly blacklisted. The remove_contact
        method is called and the contact's id is added to the _blacklist set.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        r.remove_contact = MagicMock()
        r.blacklist(contact)
        r.remove_contact.called_once_with(contact, True)
        self.assertIn(contact.network_id, r._blacklist)

    def test_add_contact_with_parent_node_id(self):
        """
        If the newly discovered contact is, in fact, this node then it's not
        added to the routing table.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        contact.network_id = parent_node_id
        r.add_contact(contact)
        self.assertEqual(len(r._buckets[0]), 0)

    def test_add_contact_with_blacklisted_contact(self):
        """
        If the newly discovered contact is, in fact, already in the local
        node's blacklist then ensure it doesn't get re-added.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        contact1.network_id = hex(2)
        contact2 = PeerNode(PUBLIC_KEY, '192.168.0.2', 9999, 0)
        contact2.network_id = hex(4)
        r.blacklist(contact2)
        r.add_contact(contact1)
        self.assertEqual(len(r._buckets[0]), 1)
        r.add_contact(contact2)
        self.assertEqual(len(r._buckets[0]), 1)

    def test_add_contact_simple(self):
        """
        Ensures that a newly discovered node in the network is added to the
        correct bucket in the routing table.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, '192.168.0.1', 9999, 0)
        contact1.network_id = hex(2)
        contact2 = PeerNode(PUBLIC_KEY, '192.168.0.2', 9999, 0)
        contact2.network_id = hex(4)
        r.add_contact(contact1)
        self.assertEqual(len(r._buckets[0]), 1)
        r.add_contact(contact2)
        self.assertEqual(len(r._buckets[0]), 2)

    def test_add_contact_with_bucket_split(self):
        """
        Ensures that newly discovered nodes are added to the appropriate
        bucket given a bucket split.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        for i in range(20):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        # This id will be just over the max range for the bucket in position 0
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.20:9999/', 0)
        large_id = int(((2 ** 512) / 2) + 1)
        contact.network_id = hex(large_id)
        r.add_contact(contact)
        self.assertEqual(len(r._buckets), 2)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertEqual(len(r._buckets[1]), 1)

    def test_add_contact_with_bucket_full(self):
        """
        Checks if a bucket is full and a new contact within the full bucket's
        range is added then it gets put in the replacement cache.
        """
        parent_node_id = hex((2 ** 512)+1)[2:]
        r = RoutingTable(parent_node_id)
        # Fill up the bucket
        for i in range(20):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        # Create a new contact that will be added to the replacement cache.
        contact = PeerNode(PUBLIC_KEY, self.version,
                           'netstring://192.168.0.20:9999/', 0)
        contact.network_id = hex(20)
        r.add_contact(contact)
        cache_key = (r._buckets[0].range_min, r._buckets[0].range_max)
        self.assertTrue(cache_key in r._replacement_cache)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertEqual(contact, r._replacement_cache[cache_key][0])

    def test_add_contact_with_full_replacement_cache(self):
        """
        Ensures that if the replacement cache is full (length = k) then the
        oldest contact within the cache is replaced with the new contact that
        was just seen.
        """
        parent_node_id = hex((2 ** 512)+1)[2:]
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        # Sanity check of the replacement cache.
        cache_key = (r._buckets[0].range_min, r._buckets[0].range_max)
        self.assertEqual(len(r._replacement_cache[cache_key]), 20)
        self.assertEqual(hex(20),
                         r._replacement_cache[cache_key][0].network_id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = PeerNode(PUBLIC_KEY, self.version,
                               'netstring://192.168.0.20:9999/', 0)
        new_contact.network_id = hex(40)
        r.add_contact(new_contact)
        self.assertEqual(len(r._replacement_cache[cache_key]), 20)
        self.assertEqual(new_contact, r._replacement_cache[cache_key][19])
        self.assertEqual(hex(21),
                         r._replacement_cache[cache_key][0].network_id)

    def test_add_contact_with_existing_contact_in_replacement_cache(self):
        """
        Ensures that if the contact to be put in the replacement cache already
        exists in the replacement cache then it is bumped to the most recent
        position.
        """
        parent_node_id = hex((2 ** 512)+1)[2:]
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        # Sanity check of the replacement cache.
        cache_key = (r._buckets[0].range_min, r._buckets[0].range_max)
        self.assertEqual(len(r._replacement_cache[cache_key]), 20)
        self.assertEqual(hex(20),
                         r._replacement_cache[cache_key][0].network_id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = PeerNode(PUBLIC_KEY, self.version,
                               'netstring://192.168.0.41:9999/', 0)
        new_contact.network_id = hex(20)
        r.add_contact(new_contact)
        self.assertEqual(len(r._replacement_cache[cache_key]), 20)
        self.assertEqual(new_contact, r._replacement_cache[cache_key][19])
        self.assertEqual(hex(21),
                         r._replacement_cache[cache_key][0].network_id)

    def test_find_close_nodes_single_bucket(self):
        """
        Ensures K number of closest nodes get returned.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        result = r.find_close_nodes(hex(1))
        self.assertEqual(constants.K, len(result))

    def test_find_close_nodes_fewer_than_K(self):
        """
        Ensures that all close nodes are returned if their number is < K.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(10):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        result = r.find_close_nodes(hex(1))
        self.assertEqual(10, len(result))

    def test_find_close_nodes_multiple_buckets(self):
        """
        Ensures that nodes are returned from neighbouring k-buckets if the
        k-bucket containing the referenced ID doesn't contain K entries.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(512):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            r.add_contact(contact)
        result = r.find_close_nodes(hex(2 ** 256))
        self.assertEqual(constants.K, len(result))

    def test_find_close_nodes_exclude_contact(self):
        """
        Ensure that nearest nodes are returned except for the specified
        excluded node.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(20):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(i)
            r.add_contact(contact)
        result = r.find_close_nodes(hex(1), excluded_id=contact.network_id)
        self.assertEqual(constants.K - 1, len(result))

    def test_find_close_nodes_in_correct_order(self):
        """
        Ensures that the nearest nodes are returned in the correct order: from
        the node closest to the target key to the node furthest away.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(512):
            uri = 'netstring://192.168.0.%d:9999/' % i
            contact = PeerNode(PUBLIC_KEY, self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            r.add_contact(contact)
        target_key = hex(2 ** 256)
        result = r.find_close_nodes(target_key)
        self.assertEqual(constants.K, len(result))

        # Ensure results are in the correct order.
        def key(node):
            return distance(node.network_id, target_key)
        sorted_nodes = sorted(result, key=key)
        self.assertEqual(sorted_nodes, result)
        # Ensure the order is from lowest to highest in terms of distance
        distances = [distance(x.network_id, target_key) for x in result]
        self.assertEqual(sorted(distances), distances)

    def test_get_contact(self):
        """
        Ensures that the correct contact is returned.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        r.add_contact(contact1)
        result = r.get_contact('a')
        self.assertEqual(contact1, result)

    def test_get_contact_does_not_exist(self):
        """
        Ensures that a ValueError is returned if the referenced contact does
        not exist in the routing table.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        r.add_contact(contact1)
        self.assertRaises(ValueError, r.get_contact, 'b')

    def test_get_refresh_list(self):
        """
        Ensures that only keys from stale k-buckets are returned.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket1 = Bucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.last_accessed = time.time() - 3700
        r._buckets[0] = bucket1
        bucket2 = Bucket(2, 3)
        bucket2.last_accessed = time.time()
        r._buckets.append(bucket2)
        expected = 1
        result = r.get_refresh_list(0)
        self.assertEqual(1, len(result))
        self.assertEqual(expected, int(result[0], 0))

    def test_get_forced_refresh_list(self):
        """
        Ensures that keys from all k-buckets (no matter if they're stale or
        not) are returned.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        bucket1 = Bucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.last_accessed = time.time() - 3700
        r._buckets[0] = bucket1
        bucket2 = Bucket(2, 3)
        bucket2.last_accessed = time.time()
        r._buckets.append(bucket2)
        result = r.get_refresh_list(0, True)
        # Even though bucket 2 is not stale it still has a key for it in
        # the result.
        self.assertEqual(2, len(result))
        self.assertEqual(1, int(result[0], 0))
        self.assertEqual(2, int(result[1], 0))

    def test_remove_contact(self):
        """
        Ensures that a contact is removed, given that it's failedRPCs counter
        exceeds or is equal to constants.ALLOWED_RPC_FAILS
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        contact2 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact2.network_id = 'b'
        r.add_contact(contact1)
        # contact2 will have the wrong number of failedRPCs
        r.add_contact(contact2)
        contact2.failed_RPCs = constants.ALLOWED_RPC_FAILS
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.remove_contact('b')
        self.assertEqual(len(r._buckets[0]), 1)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])

    def test_remove_contact_with_unknown_contact(self):
        """
        Ensures that attempting to remove a non-existent contact results in
        no change.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        r.add_contact(contact1)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 1)
        result = r.remove_contact('b')
        self.assertEqual(None, result)
        self.assertEqual(len(r._buckets[0]), 1)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])

    def test_remove_contact_with_cached_replacement(self):
        """
        Ensures that the removed contact is replaced by the most up-to-date
        contact in the affected k-bucket's cache.
        """
        parent_node_id = hex((2 ** 512)+1)[2:]
        r = RoutingTable(parent_node_id)
        cache_key = (r._buckets[0].range_min, r._buckets[0].range_max)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        contact2 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact2.network_id = 'b'
        r.add_contact(contact1)
        # contact2 will have the wrong number of failedRPCs
        r.add_contact(contact2)
        contact2.failed_RPCs = constants.ALLOWED_RPC_FAILS
        # Add something into the cache.
        contact3 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact3.network_id = '3'
        r._replacement_cache[cache_key] = [contact3, ]
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(len(r._replacement_cache[cache_key]), 1)

        r.remove_contact('b')
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])
        self.assertEqual(contact3, r._buckets[0]._contacts[1])
        self.assertEqual(len(r._replacement_cache[cache_key]), 0)

    def test_remove_contact_with_not_enough_RPC_fails(self):
        """
        Ensures that the contact is not removed if it's failedRPCs counter is
        less than constants.ALLOWED_RPC_FAILS
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        contact2 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact2.network_id = 'b'
        r.add_contact(contact1)
        r.add_contact(contact2)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.remove_contact('b')
        self.assertEqual(len(r._buckets[0]), 2)

    def test_remove_contact_with_not_enough_RPC_but_forced(self):
        """
        Ensures that the contact is removed despite it's failedRPCs counter
        being less than constants.ALLOWED_RPC_FAILS because the 'forced' flag
        is used.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        contact2 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact2.network_id = 'b'
        r.add_contact(contact1)
        r.add_contact(contact2)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.remove_contact('b', forced=True)
        self.assertEqual(len(r._buckets[0]), 1)

    def test_remove_contact_removes_from_replacement_cache(self):
        """
        Ensures that if a contact is signalled to be removed it is also cleared
        from the replacement_cache that would otherwise be another route for
        it to be re-added to the routing table.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        contact1 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact1.network_id = 'a'
        contact2 = PeerNode(PUBLIC_KEY, self.version,
                            'netstring://192.168.0.1:9999/', 0)
        contact2.network_id = 'b'
        r.add_contact(contact1)
        r.add_contact(contact2)
        cache_key = (r._buckets[0].range_min, r._buckets[0].range_max)
        r._replacement_cache[cache_key] = []
        r._replacement_cache[cache_key].append(contact2)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(len(r._replacement_cache[cache_key]), 1)

        r.remove_contact('b', forced=True)
        self.assertEqual(len(r._buckets[0]), 1)
        self.assertNotIn(contact2, r._replacement_cache[cache_key])

    def test_touch_bucket(self):
        """
        Ensures that the last_accessed field of the affected k-bucket isi
        updated appropriately.
        """
        parent_node_id = 'deadbeef'
        r = RoutingTable(parent_node_id)
        # At this point the single k-bucket in the routing table will have a
        # lastAccessed time of 0 (zero). Sanity check.
        self.assertEqual(0, r._buckets[0].last_accessed)
        # Since all keys are in the range of the single k-bucket any key will
        # do for the purposes of testing.
        r.touch_bucket('abc')
        self.assertNotEqual(0, r._buckets[0].last_accessed)
