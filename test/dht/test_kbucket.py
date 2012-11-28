# -*- coding: utf-8 -*-
"""
Ensures the kbucket (used to store contacts in the network) works as expected.
"""
from drogulus.dht.kbucket import KBucket, KBucketFull
from drogulus.dht.contact import Contact
from drogulus.dht.constants import K
import unittest


class TestKBucket(unittest.TestCase):
    """
    Ensures the KBucket class works as expected.
    """

    def test_init(self):
        """
        Ensures an object is created as expected.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        # Min/Max are set correctly
        self.assertEqual(range_min, bucket.range_min,
                         "KBucket rangeMin not set correctly.")
        self.assertEqual(range_max, bucket.range_max,
                         "KBucket rangeMax not initialised correctly.")
        # The contacts list exists and is empty
        self.assertEqual([], bucket._contacts,
                         "KBucket contact list not initialised correctly.")
        # Last access timestamp is correct
        self.assertEqual(0, bucket.last_accessed)

    def test_add_new_contact(self):
        """
        Ensures that a new contact, when added to the kbucket is appended to
        the end of the _contacts list (as specified in the original Kademlia
        paper) signifying that it is the most recently seen contact within
        this bucket.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        contact1 = Contact("1", "192.168.0.1", 9999, 123)
        bucket.add_contact(contact1)
        self.assertEqual(1, len(bucket._contacts),
                         "Single contact not added to k-bucket.")
        contact2 = Contact("2", "192.168.0.2", 8888, 123)
        bucket.add_contact(contact2)
        self.assertEqual(2, len(bucket._contacts),
                         "K-bucket's contact list not the expected length.")
        self.assertEqual(contact2, bucket._contacts[-1:][0],
                         "K-bucket's most recent (last) contact wrong.")

    def test_add_existing_contact(self):
        """
        Ensures that if an existing contact is re-added to the kbucket it is
        simply moved to the end of the _contacts list (as specified in the
        original Kademlia paper) signifying that it is the most recently seen
        contact within this bucket.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        contact1 = Contact("1", "192.168.0.1", 9999, 123)
        bucket.add_contact(contact1)
        contact2 = Contact("2", "192.168.0.2", 8888, 123)
        bucket.add_contact(contact2)
        bucket.add_contact(contact1)
        # There should still only be two contacts in the bucket.
        self.assertEqual(2, len(bucket._contacts),
                         "Too many contacts in the k-bucket.")
        # The end contact should be the most recently added contact.
        self.assertEqual(contact1, bucket._contacts[-1:][0],
                         "The expected most recent contact is wrong.")

    def test_add_contact_to_full_bucket(self):
        """
        Ensures that if one attempts to add a contact to a bucket whose size is
        greater than the constant K, then the KBucketFull exception is raised.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        with self.assertRaises(KBucketFull):
            contact_too_many = Contact("12345", "192.168.0.2", 8888, 123)
            bucket.add_contact(contact_too_many)

    def test_get_contact(self):
        """
        Ensures it is possible to get a contact from the k-bucket with a valid
        id.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        for i in range(K):
            self.assertTrue(bucket.get_contact("%d" % i),
                            "Could not get contact with id %d" % i)

    def test_get_contact_with_bad_id(self):
        """
        Ensures a ValueError exception is raised if one attempts to get a
        contact from the k-bucket with an id that doesn't exist in the
        k-bucket.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.add_contact(contact)
        with self.assertRaises(ValueError):
            bucket.get_contact("54321")

    def test_get_contacts_all(self):
        """
        Ensures get_contacts works as expected.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        result = bucket.get_contacts()
        self.assertEqual(20, len(result))

    def test_get_contacts_empty(self):
        """
        If the k-bucket is empty, the result of getContacts is an empty list.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        result = bucket.get_contacts()
        self.assertEqual(0, len(result))

    def test_get_contacts_count_too_big(self):
        """
        If the "count" argument is bigger than the number of contacts in the
        bucket then all the contacts are returned.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(10):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        result = bucket.get_contacts(count=20)
        self.assertEqual(10, len(result))

    def test_get_contacts_with_exclusion(self):
        """
        If a contact is passed as the excludeContact argument then it won't be
        in the result list.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        result = bucket.get_contacts(count=20, exclude_contact=contact)
        self.assertEqual(19, len(result))
        self.assertFalse(contact in result)

    def test_remove_contact(self):
        """
        Ensures it is possible to remove a contact with a certain ID from the
        k-bucket.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.add_contact(contact)
        for i in range(K):
            id = "%d" % i
            bucket.remove_contact(id)
            self.assertFalse(id in bucket._contacts,
                             "Could not remove contact with id %d" % i)

    def test_remove_contact_with_bad_id(self):
        """
        Ensures a ValueError exception is raised if one attempts to remove a
        non-existent contact from a k-bucket.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.add_contact(contact)
        with self.assertRaises(ValueError):
            bucket.remove_contact("54321")

    def test_key_in_range_yes(self):
        """
        Ensures that a key within the appropriate range is identified as such.
        """
        bucket = KBucket(1, 9)
        self.assertTrue(bucket.key_in_range(2))

    def test_key_in_range_no_too_low(self):
        """
        Ensures a key just below the k-bucket's range is identified as out of
        range.
        """
        bucket = KBucket(5, 9)
        self.assertFalse(bucket.key_in_range(2))

    def test_key_in_range_no_too_high(self):
        """
        Ensures a key just above the k-bucket's range is identified as out of
        range.
        """
        bucket = KBucket(1, 5)
        self.assertFalse(bucket.key_in_range(7))

    def test_key_in_range_handles_string(self):
        """
        Ensures the keyInRange method decodes a string representation of a key
        correctly, before testing if it's within range.
        """
        bucket = KBucket(1, 66)
        self.assertTrue(bucket.key_in_range('A'))

    def test_len(self):
        """
        Ensures the number of nodes in the k-bucket is returned by __len__.
        """
        range_min = 12345
        range_max = 98765
        bucket = KBucket(range_min, range_max)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.add_contact(contact)
        self.assertEqual(1, len(bucket))
