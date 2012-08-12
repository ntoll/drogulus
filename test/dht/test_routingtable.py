"""
Ensures the routing table (a binary tree used to link kbuckets with key ranges
in the DHT) works as expected.
"""
from drogulus.dht.routingtable import RoutingTable
from drogulus.dht.contact import Contact
from drogulus.dht.kbucket import KBucket, KBucketFull
from drogulus.dht import constants
import unittest
import time

class TestRoutingTable(unittest.TestCase):
    """
    Ensures the RoutingTable class works as expected.
    """

    def testInit(self):
        """
        Ensures an object is created as expected.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Ensure the initial kbucket is created.
        self.assertEqual(1, len(r._buckets))
        # Ensure the parent's node ID is stored.
        self.assertEqual(parentNodeID, r._parentNodeID)

    def test_kbucketIndex(self):
        """
        Ensures the expected index is returned.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # a simple test with only one kbucket in the routing table.
        test_key = 'abc123'
        expected_index = 0
        actual_index = r._kbucketIndex(test_key)
        self.assertEqual(expected_index, actual_index)
        # a more complex test with multiple kbuckets.
        r._splitBucket(0)
        split_point = (2**160)/2
        lower_key = split_point - 1
        higher_key = split_point + 1
        expected_lower_index = 0
        expected_higher_index = 1
        actual_lower_index = r._kbucketIndex(lower_key)
        actual_higher_index = r._kbucketIndex(higher_key)
        self.assertEqual(expected_lower_index, actual_lower_index)
        self.assertEqual(expected_higher_index, actual_higher_index)

    def test_randomKeyInBucketRange(self):
        """
        Ensures the returned key is within the expected bucket range.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        rangeMin = 1
        rangeMax = 2
        bucket = KBucket(rangeMin, rangeMax)
        r._buckets[0] = bucket
        expected = 1
        actual = int(r._randomKeyInBucketRange(0).encode('hex'), 16)
        self.assertEqual(expected, actual)

    def test_splitBucket(self):
        """
        Ensures that the correct bucket is split in two and that the contacts
        are found in the right place.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        rangeMin = 0
        rangeMax = 10
        bucket = KBucket(rangeMin, rangeMax)
        contact1 = Contact(2, '192.168.0.1', 9999, 0)
        bucket.addContact(contact1)
        contact2 = Contact(4, '192.168.0.2', 8888, 0)
        bucket.addContact(contact2)
        contact3 = Contact(6, '192.168.0.3', 8888, 0)
        bucket.addContact(contact3)
        contact4 = Contact(8, '192.168.0.4', 8888, 0)
        bucket.addContact(contact4)
        r._buckets[0] = bucket
        # Sanity check
        self.assertEqual(1, len(r._buckets))
        r._splitBucket(0)
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
        r._splitBucket(1)
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
        r._splitBucket(0)
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

    def testAddContactWithParentNodeID(self):
        """
        If the newly discovered contact is, in fact, this node then it's not
        added to the routing table.
        """
        parentNodeID = 123
        r = RoutingTable(parentNodeID)
        contact = Contact(123, '192.168.0.1', 9999, 0)
        r.addContact(contact)
        self.assertEqual(len(r._buckets[0]), 0)

    def testAddContactSimple(self):
        """
        Ensures that a newly discovered node in the network is added to the
        correct kbucket in the routing table.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact(2, '192.168.0.1', 9999, 0)
        contact2 = Contact(4, '192.168.0.2', 9999, 0)
        r.addContact(contact1)
        self.assertEqual(len(r._buckets[0]), 1)
        r.addContact(contact2)
        self.assertEqual(len(r._buckets[0]), 2)

    def testAddContactWithBucketSplit(self):
        """
        Ensures that newly discovered nodes are added to the appropriate
        kbucket given a bucket split.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        for i in range(20):
            contact = Contact(i, '192.168.0.%d' % i, 0)
            r.addContact(contact)
        # This id will be just over the max range for the bucket in position 0
        large_id = 730750818665451459101842416358141509827966271489L
        contact = Contact(large_id, '192.168.0.33', 0)
        r.addContact(contact)
        self.assertEqual(len(r._buckets), 2)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertEqual(len(r._buckets[1]), 1)

    def testAddContactWithBucketFull(self):
        """
        Checks if a bucket is full and a new contact within the full bucket's
        range is added then it gets put in the replacement cache.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket
        for i in range(20):
            contact = Contact(i, '192.168.0.%d' % i, 0)
            r.addContact(contact)
        # Create a new contact that will be added to the replacement cache.
        contact = Contact(20, '192.168.0.20', 0)
        r.addContact(contact)
        self.assertEqual(len(r._buckets[0]), 20)
        self.assertTrue(0 in r._replacementCache)
        self.assertEqual(contact, r._replacementCache[0][0])

    def testAddContactWithFullReplacementCache(self):
        """
        Ensures that if the replacement cache is full (length = k) then the
        oldest contact within the cache is replaced with the new contact that
        was just seen.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(i, "192.168.0.%d" % i, 0)
            r.addContact(contact)
        # Sanity check of the replacement cache.
        self.assertEqual(len(r._replacementCache[0]), 20)
        self.assertEqual(20, r._replacementCache[0][0].id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = Contact(40, "192.168.0.20", 0)
        r.addContact(new_contact)
        self.assertEqual(len(r._replacementCache[0]), 20)
        self.assertEqual(new_contact, r._replacementCache[0][19])
        self.assertEqual(21, r._replacementCache[0][0].id)

    def testAddContactWithExistingContactInReplacementCache(self):
        """
        Ensures that if the contact to be put in the replacement cache already
        exists in the replacement cache then it is bumped to the most recent
        position.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(i, '192.168.0.%d' % i, 0)
            r.addContact(contact)
        # Sanity check of the replacement cache.
        self.assertEqual(len(r._replacementCache[0]), 20)
        self.assertEqual(20, r._replacementCache[0][0].id)
        # Create a new contact that will be added to the replacement cache.
        new_contact = Contact(20, '192.168.0.20', 0)
        r.addContact(new_contact)
        self.assertEqual(len(r._replacementCache[0]), 20)
        self.assertEqual(new_contact, r._replacementCache[0][19])
        self.assertEqual(21, r._replacementCache[0][0].id)

    def testDistance(self):
        """
        Sanity check to ensure the XOR'd values return the correct distance.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        key1 = 'abc'
        key2 = 'xyz'
        expected = 1645337L
        actual = r.distance(key1, key2)
        self.assertEqual(expected, actual)

    def testFindCloseNodesSingleKBucket(self):
        """
        Ensures K number of closest nodes get returned.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(40):
            contact = Contact(i, "192.168.0.%d" % i, 0)
            r.addContact(contact)
        result = r.findCloseNodes(1)
        self.assertEqual(20, len(result))

    def testFindCloseNodesFewerThanK(self):
        """
        Ensures that all close nodes are returned if their number is < K.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(10):
            contact = Contact(i, "192.168.0.%d" % i, 0)
            r.addContact(contact)
        result = r.findCloseNodes(1)
        self.assertEqual(10, len(result))

    def testFindCloseNodesMultipleBuckets(self):
        """
        Ensures that nodes are returned from neighbouring k-buckets if the
        k-bucket containing the referenced ID doesn't contain K entries.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(160):
            contact = Contact(2 ** i, "192.168.0.%d" % i, 0)
            r.addContact(contact)
        result = r.findCloseNodes(2 ** 80)
        self.assertEqual(20, len(result))

    def testFindCloseNodesExcludeContact(self):
        """
        Ensure that nearest nodes are returned except for the specified
        excluded node.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # Fill up the bucket and replacement cache
        for i in range(20):
            contact = Contact(str(i), "192.168.0.%d" % i, 0)
            r.addContact(contact)
        result = r.findCloseNodes("1", rpcNodeID=contact)
        self.assertEqual(19, len(result))

    def testGetContact(self):
        """
        Ensures that the correct contact is returned.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact('a', '192.168.0.1', 9999, 0)
        r.addContact(contact1)
        result = r.getContact('a')
        self.assertEqual(contact1, result)

    def testGetContact(self):
        """
        Ensures that a ValueError is returned if the referenced contact does
        not exist in the routing table.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact('a', '192.168.0.1', 9999, 0)
        r.addContact(contact1)
        self.assertRaises(ValueError, r.getContact, 'b')

    def testGetRefreshList(self):
        """
        Ensures that only keys from stale k-buckets are returned.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        bucket1 = KBucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.lastAccessed = int(time.time()) - 3700
        r._buckets[0] = bucket1
        bucket2 = KBucket(2, 3)
        bucket2.lastAccessed = int(time.time())
        r._buckets.append(bucket2)
        expected = 1
        result = r.getRefreshList(0)
        self.assertEqual(1, len(result))
        self.assertEqual(expected, int(result[0].encode('hex'), 16))

    def testGetForcedRefreshList(self):
        """
        Ensures that keys from all k-buckets (no matter if they're stale or
        not) are returned.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        bucket1 = KBucket(1, 2)
        # Set the lastAccessed flag on bucket 1 to be out of date
        bucket1.lastAccessed = int(time.time()) - 3700
        r._buckets[0] = bucket1
        bucket2 = KBucket(2, 3)
        bucket2.lastAccessed = int(time.time())
        r._buckets.append(bucket2)
        result = r.getRefreshList(0, True)
        # Even though bucket 2 is not stale it still has a key for it in
        # the result.
        self.assertEqual(2, len(result))
        self.assertEqual(1, int(result[0].encode('hex'), 16))
        self.assertEqual(2, int(result[1].encode('hex'), 16))

    def testRemoveContact(self):
        """
        Ensures that a contact is removed, given that it's failedRPCs counter
        exceeds or is equal to constants.ALLOWED_RPC_FAILS
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact('a', '192.168.0.1', 9999, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, 0)
        r.addContact(contact1)
        # Contact 2 will have the wrong number of failedRPCs
        r.addContact(contact2)
        contact2.failedRPCs = constants.ALLOWED_RPC_FAILS
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.removeContact('b')
        self.assertEqual(len(r._buckets[0]), 1)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])

    def testRemoveContactWithCachedReplacement(self):
        """
        Ensures that the removed contact is replaced by the most up-to-date
        contact in the affected k-bucket's cache.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact('a', '192.168.0.1', 9999, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, 0)
        r.addContact(contact1)
        # Contact 2 will have the wrong number of failedRPCs
        r.addContact(contact2)
        contact2.failedRPCs = constants.ALLOWED_RPC_FAILS
        # Add something into the cache.
        contact3 = Contact('c', '192.168.0.3', 9999, 0)
        r._replacementCache[0] = [contact3, ]
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(len(r._replacementCache[0]), 1)

        r.removeContact('b')
        self.assertEqual(len(r._buckets[0]), 2)
        self.assertEqual(contact1, r._buckets[0]._contacts[0])
        self.assertEqual(contact3, r._buckets[0]._contacts[1])
        self.assertEqual(len(r._replacementCache[0]), 0)

    def testRemoveContactWithNotEnoughRPCFails(self):
        """
        Ensures that the contact is not removed if it's failedRPCs counter is
        less than constants.ALLOWED_RPC_FAILS
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        contact1 = Contact('a', '192.168.0.1', 9999, 0)
        contact2 = Contact('b', '192.168.0.2', 9999, 0)
        r.addContact(contact1)
        r.addContact(contact2)
        # Sanity check
        self.assertEqual(len(r._buckets[0]), 2)

        r.removeContact('b')
        self.assertEqual(len(r._buckets[0]), 2)

    def testTouchKBucket(self):
        """
        Ensures that the lastAccessed field of the affected k-bucket is updated
        appropriately.
        """
        parentNodeID = 'abc'
        r = RoutingTable(parentNodeID)
        # At this point the single k-bucket in the routing table will have a
        # lastAccessed time of 0 (zero). Sanity check.
        self.assertEqual(0, r._buckets[0].lastAccessed)
        # Since all keys are in the range of the single k-bucket any key will
        # do for the purposes of testing.
        r.touchKBucket('xyz')
        self.assertNotEqual(0, r._buckets[0].lastAccessed)
