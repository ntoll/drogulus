"""
Ensures the routing table (a binary tree used to link kbuckets with key ranges
in the DHT) works as expected.
"""
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.contact import Contact
from drogulus.dht.kbucket import KBucket
from drogulus.dht import constants
from drogulus.version import get_version
import unittest
import time


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
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Ensure the initial kbucket is created.
        self.assertEqual(1, len(r._buckets))
        # Ensure the parent's node ID is stored.
        self.assertEqual(parent_node_id, r._parent_node_id)

    def test_kbucket_index_single_bucket(self):
        """
        Ensures the expected index is returned when only a single bucket
        exists.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # a simple test with only one kbucket in the routing table.
        test_key = 'abc123'
        expected_index = 0
        actual_index = r._kbucket_index(test_key)
        self.assertEqual(expected_index, actual_index)

    def test_kbucket_index_multiple_buckets(self):
        """
        Ensures the expected index is returned when multiple buckets exist.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        r._split_bucket(0)
        split_point = (2 ** 512) / 2
        lower_key = split_point - 1
        higher_key = split_point + 1
        expected_lower_index = 0
        expected_higher_index = 1
        actual_lower_index = r._kbucket_index(lower_key)
        actual_higher_index = r._kbucket_index(higher_key)
        self.assertEqual(expected_lower_index, actual_lower_index)
        self.assertEqual(expected_higher_index, actual_higher_index)

    def test_kbucket_index_as_string_and_int(self):
        """
        Ensures that the specified key can be expressed as both a string
        and integer value.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # key as a string
        test_key = 'abc123'
        expected_index = 0
        actual_index = r._kbucket_index(test_key)
        self.assertEqual(expected_index, actual_index)
        # key as an integer
        test_key = 1234567
        actual_index = r._kbucket_index(test_key)
        self.assertEqual(expected_index, actual_index)

    def test_kbucket_index_out_of_range(self):
        """
        If the requested id is not within the range of the keyspace then a
        ValueError should be raised.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Populate the routing table with contacts.
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        with self.assertRaises(ValueError):
            # Incoming id that's too small.
            r.find_close_nodes(-1)
        with self.assertRaises(ValueError):
            # Incoming id that's too big
            big_id = 2 ** 512
            r.find_close_nodes(big_id)

    def test_random_key_in_bucket_range(self):
        """
        Ensures the returned key is within the expected bucket range.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        bucket = KBucket(1, 2)
        r._buckets[0] = bucket
        expected = 1
        actual = int(r._random_key_in_bucket_range(0).encode('hex'), 16)
        self.assertEqual(expected, actual)

    def test_random_key_in_bucket_range_long(self):
        """
        Ensures that random_key_in_bucket_range works with large numbers.
        """
        minimum = 978675645342314253647586978
        maximum = 978675645342314253647586979
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        bucket = KBucket(minimum, maximum)
        r._buckets[0] = bucket
        expected = minimum
        actual = int(r._random_key_in_bucket_range(0).encode('hex'), 16)
        self.assertEqual(expected, actual)

    def test_split_bucket(self):
        """
        Ensures that the correct bucket is split in two and that the contacts
        are found in the right place.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        bucket = KBucket(0, 10)
        contact1 = Contact(2, '192.168.0.1', 9999, 0)
        bucket.add_contact(contact1)
        contact2 = Contact(4, '192.168.0.2', 8888, 0)
        bucket.add_contact(contact2)
        contact3 = Contact(6, '192.168.0.3', 8888, 0)
        bucket.add_contact(contact3)
        contact4 = Contact(8, '192.168.0.4', 8888, 0)
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
        # kbucket1 remains un-changed
        self.assertEqual(2, len(bucket1._contacts))
        # kbucket2 only contains the lower half of its original contacts.
        self.assertEqual(1, len(bucket2._contacts))
        self.assertEqual(contact3, bucket2._contacts[0])
        # kbucket3 now contains the upper half of the original contacts.
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

    def test_add_contact_with_parent_node_id(self):
        """
        If the newly discovered contact is, in fact, this node then it's not
        added to the routing table.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact = Contact('abc', '192.168.0.1', 9999, 0)
        r.add_contact(contact)
        self.assertEqual(len(r._buckets[0]), 0)

    def test_add_contact_simple(self):
        """
        Ensures that a newly discovered node in the network is added to the
        correct kbucket in the routing table.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact(2, '192.168.0.1', 9999, 0)
        contact2 = Contact(4, '192.168.0.2', 9999, 0)
        r.add_contact(contact1)
        self.assertEqual(len(r._buckets[0]), 1)
        r.add_contact(contact2)
        self.assertEqual(len(r._buckets[0]), 2)

    def test_add_contact_with_bucket_split(self):
        """
        Ensures that newly discovered nodes are added to the appropriate
        kbucket given a bucket split.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        for i in range(20):
            contact = Contact(i, '192.168.0.%d' % i, self.version, 0)
            r.add_contact(contact)
        # This id will be just over the max range for the bucket in position 0
        large_id = ((2 ** 512) / 2) + 1
        contact = Contact(large_id, '192.168.0.33', self.version, 0)
        r.add_contact(contact)
        self.assertEqual(len(r._buckets), 2)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertEqual(len(r._buckets[1]), 1)

    def test_add_contact_with_bucket_full(self):
        """
        Checks if a bucket is full and a new contact within the full bucket's
        range is added then it gets put in the replacement cache.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket
        for i in range(20):
            contact = Contact(i, '192.168.0.%d' % i, self.version, 0)
            r.add_contact(contact)
        # Create a new contact that will be added to the replacement cache.
        contact = Contact(20, '192.168.0.20', self.version, 0)
        r.add_contact(contact)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertTrue(0 in r._replacement_cache)
        self.assertEqual(contact, r._replacement_cache[0][0])

    def test_add_contact_with_full_replacement_cache(self):
        """
        Ensures that if the replacement cache is full (length = k) then the
        oldest contact within the cache is replaced with the new contact that
        was just seen.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(str(i), "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        # Sanity check of the replacement cache.
        self.assertEqual(len(r._replacement_cache[0]), 20)
        self.assertEqual('20', r._replacement_cache[0][0].id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = Contact('40', "192.168.0.20", self.version, 0)
        r.add_contact(new_contact)
        self.assertEqual(len(r._replacement_cache[0]), 20)
        self.assertEqual(new_contact, r._replacement_cache[0][19])
        self.assertEqual('21', r._replacement_cache[0][0].id)

    def test_add_contact_with_existing_contact_in_replacement_cache(self):
        """
        Ensures that if the contact to be put in the replacement cache already
        exists in the replacement cache then it is bumped to the most recent
        position.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(str(i), '192.168.0.%d' % i, self.version, 0)
            r.add_contact(contact)
        # Sanity check of the replacement cache.
        self.assertEqual(len(r._replacement_cache[0]), 20)
        self.assertEqual('20', r._replacement_cache[0][0].id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = Contact('20', '192.168.0.20', self.version, 0)
        r.add_contact(new_contact)
        self.assertEqual(len(r._replacement_cache[0]), 20)
        self.assertEqual(new_contact, r._replacement_cache[0][19])
        self.assertEqual('21', r._replacement_cache[0][0].id)

    def test_add_contact_id_out_of_range(self):
        """
        Ensures a Contact with an out-of-range id cannot be added to the
        routing table.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        with self.assertRaises(TypeError):
            # id too small
            contact = Contact(-1, '192.168.0.1', self.version, 0)
            r.add_contact(contact)
        with self.assertRaises(ValueError):
            # id too big
            big_id = (2 ** 512)
            contact = Contact(big_id, '192.168.0.1', self.version, 0)
            r.add_contact(contact)

    def test_distance(self):
        """
        Sanity check to ensure the XOR'd values return the correct distance.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        key1 = 'abc'
        key2 = 'xyz'
        expected = 1645337L
        actual = r.distance(key1, key2)
        self.assertEqual(expected, actual)

    def test_find_close_nodes_single_kbucket(self):
        """
        Ensures K number of closest nodes get returned.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(i, "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        result = r.find_close_nodes(1)
        self.assertEqual(20, len(result))

    def test_find_close_nodes_fewer_than_K(self):
        """
        Ensures that all close nodes are returned if their number is < K.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(10):
            contact = Contact(i, "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        result = r.find_close_nodes(1)
        self.assertEqual(10, len(result))

    def test_find_close_nodes_multiple_buckets(self):
        """
        Ensures that nodes are returned from neighbouring k-buckets if the
        k-bucket containing the referenced ID doesn't contain K entries.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        result = r.find_close_nodes(2 ** 256)
        self.assertEqual(20, len(result))

    def test_find_close_nodes_exclude_contact(self):
        """
        Ensure that nearest nodes are returned except for the specified
        excluded node.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # Fill up the bucket and replacement cache
        for i in range(20):
            contact = Contact(str(i), "192.168.0.%d" % i, self.version, 0)
            r.add_contact(contact)
        result = r.find_close_nodes("1", rpc_node_id=contact)
        self.assertEqual(19, len(result))

    def test_get_contact(self):
        """
        Ensures that the correct contact is returned.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        r.add_contact(contact1)
        result = r.get_contact('a')
        self.assertEqual(contact1, result)

    def test_get_contact_does_not_exist(self):
        """
        Ensures that a ValueError is returned if the referenced contact does
        not exist in the routing table.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        r.add_contact(contact1)
        self.assertRaises(ValueError, r.get_contact, 'b')

    def test_get_refresh_list(self):
        """
        Ensures that only keys from stale k-buckets are returned.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        bucket1 = KBucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.last_accessed = int(time.time()) - 3700
        r._buckets[0] = bucket1
        bucket2 = KBucket(2, 3)
        bucket2.last_accessed = int(time.time())
        r._buckets.append(bucket2)
        expected = 1
        result = r.get_refresh_list(0)
        self.assertEqual(1, len(result))
        self.assertEqual(expected, int(result[0].encode('hex'), 16))

    def test_get_forced_refresh_list(self):
        """
        Ensures that keys from all k-buckets (no matter if they're stale or
        not) are returned.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        bucket1 = KBucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.last_accessed = int(time.time()) - 3700
        r._buckets[0] = bucket1
        bucket2 = KBucket(2, 3)
        bucket2.last_accessed = int(time.time())
        r._buckets.append(bucket2)
        result = r.get_refresh_list(0, True)
        # Even though bucket 2 is not stale it still has a key for it in
        # the result.
        self.assertEqual(2, len(result))
        self.assertEqual(1, int(result[0].encode('hex'), 16))
        self.assertEqual(2, int(result[1].encode('hex'), 16))

    def test_remove_contact(self):
        """
        Ensures that a contact is removed, given that it's failedRPCs counter
        exceeds or is equal to constants.ALLOWED_RPC_FAILS
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, self.version, 0)
        r.add_contact(contact1)
        # Contact 2 will have the wrong number of failedRPCs
        r.add_contact(contact2)
        contact2.failed_RPCs = constants.ALLOWED_RPC_FAILS
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.remove_contact('b')
        self.assertEqual(len(r._buckets[0]), 1)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])

    def test_remove_contact_with_unknown_contact(self):
        """
        Ensures that attempting to remove a non-existent contact results in a
        ValueError exception.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
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
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, self.version, 0)
        r.add_contact(contact1)
        # Contact 2 will have the wrong number of failedRPCs
        r.add_contact(contact2)
        contact2.failed_RPCs = constants.ALLOWED_RPC_FAILS
        # Add something into the cache.
        contact3 = Contact('c', '192.168.0.3', 9999, self.version, 0)
        r._replacement_cache[0] = [contact3, ]
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(len(r._replacement_cache[0]), 1)

        r.remove_contact('b')
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])
        self.assertEqual(contact3, r._buckets[0]._contacts[1])
        self.assertEqual(len(r._replacement_cache[0]), 0)

    def test_remove_contact_with_not_enough_RPC_fails(self):
        """
        Ensures that the contact is not removed if it's failedRPCs counter is
        less than constants.ALLOWED_RPC_FAILS
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, self.version, 0)
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
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        contact1 = Contact('a', '192.168.0.1', 9999, self.version, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, self.version, 0)
        r.add_contact(contact1)
        r.add_contact(contact2)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.remove_contact('b', forced=True)
        self.assertEqual(len(r._buckets[0]), 1)

    def test_touch_kbucket(self):
        """
        Ensures that the lastAccessed field of the affected k-bucket is updated
        appropriately.
        """
        parent_node_id = 'abc'
        r = RoutingTable(parent_node_id)
        # At this point the single k-bucket in the routing table will have a
        # lastAccessed time of 0 (zero). Sanity check.
        self.assertEqual(0, r._buckets[0].last_accessed)
        # Since all keys are in the range of the single k-bucket any key will
        # do for the purposes of testing.
        r.touch_kbucket('xyz')
        self.assertNotEqual(0, r._buckets[0].last_accessed)
