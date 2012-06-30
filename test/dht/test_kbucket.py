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

    def testInit(self):
        """
        Ensures an object is created as expected.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        # Min/Max are set correctly
        self.assertEqual(rangeMin, bucket.rangeMin,
            "KBucket rangeMin not set correctly.")
        self.assertEqual(rangeMax, bucket.rangeMax,
            "KBucket rangeMax not initialised correctly.")
        # The contacts list exists and is empty
        self.assertEqual([], bucket._contacts,
            "KBucket contact list not initialised correctly.")

    def testAddNewContact(self):
        """
        Ensures that a new contact, when added to the kbucket is appended to
        the end of the _contacts list (as specified in the original Kademlia
        paper) signifying that it is the most recently seen contact within
        this bucket.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        contact1 = Contact("1", "192.168.0.1", 9999, 123)
        bucket.addContact(contact1)
        self.assertEqual(1, len(bucket._contacts),
            "Single contact not added to k-bucket.")
        contact2 = Contact("2", "192.168.0.2", 8888, 123)
        bucket.addContact(contact2)
        self.assertEqual(2, len(bucket._contacts),
            "K-bucket's contact list not the expected length.")
        self.assertEqual(contact2, bucket._contacts[-1:][0],
            "K-bucket's most recent (last) contact wrong.")

    def testAddExistingContact(self):
        """
        Ensures that if an existing contact is re-added to the kbucket it is
        simply moved to the end of the _contacts list (as specified in the
        original Kademlia paper) signifying that it is the most recently seen
        contact within this bucket.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        contact1 = Contact("1", "192.168.0.1", 9999, 123)
        bucket.addContact(contact1)
        contact2 = Contact("2", "192.168.0.2", 8888, 123)
        bucket.addContact(contact2)
        bucket.addContact(contact1)
        # There should still only be two contacts in the bucket.
        self.assertEqual(2, len(bucket._contacts),
            "Too many contacts in the k-bucket.")
        # The end contact should be the most recently added contact.
        self.assertEqual(contact1, bucket._contacts[-1:][0],
            "The expected most recent contact is wrong.")

    def testAddContactToFullBucket(self):
        """
        Ensures that if one attempts to add a contact to a bucket whose size is
        greater than the constant K, then the KBucketFull exception is raised.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.addContact(contact)
        with self.assertRaises(KBucketFull):
            contactTooMany = Contact("12345", "192.168.0.2", 8888, 123)
            bucket.addContact(contactTooMany)

    def testGetContact(self):
        """
        Ensures it is possible to get a contact from the k-bucket with a valid
        id.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.addContact(contact)
        for i in range(K):
            self.assertTrue(bucket.getContact("%d" % i),
                "Could not get contact with id %d" % i)

    def testGetContactWithBadID(self):
        """
        Ensures a ValueError exception is raised if one attempts to get a
        contact from the k-bucket with an id that doesn't exist in the k-bucket.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.addContact(contact)
        with self.assertRaises(ValueError):
            bucket.getContact("54321")

    def testRemoveContact(self):
        """
        Ensures it is possible to remove a contact with a certain ID from the
        k-bucket.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        for i in range(K):
            contact = Contact("%d" % i, "192.168.0.%d" % i, 9999, 123)
            bucket.addContact(contact)
        for i in range(K):
            id = "%d" % i
            bucket.removeContact(id)
            self.assertFalse(id in bucket._contacts,
                "Could not remove contact with id %d" % i)

    def testRemoveContactWithBadID(self):
        """
        Ensures a ValueError exception is raised if one attempts to remove a
        non-existent contact from a k-bucket.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.addContact(contact)
        with self.assertRaises(ValueError):
            bucket.removeContact("54321")

    def testKeyInRangeYes(self):
        """
        Ensures that a key within the appropriate range is identified as such.
        """
        rangeMin = 1
        rangeMax = 9
        bucket = KBucket(rangeMin, rangeMax)
        self.assertTrue(bucket.keyInRange(2))

    def testKeyInRangeNoToLow(self):
        """
        Ensures a key just below the k-bucket's range is identified as out of
        range.
        """
        rangeMin = 5
        rangeMax = 9
        bucket = KBucket(rangeMin, rangeMax)
        self.assertFalse(bucket.keyInRange(2))

    def testKeyInRangeNoToHigh(self):
        """
        Ensures a key just above the k-bucket's range is identified as out of
        range.
        """
        rangeMin = 1
        rangeMax = 5
        bucket = KBucket(rangeMin, rangeMax)
        self.assertFalse(bucket.keyInRange(7))

    def testKeyInRangeHandlesString(self):
        """
        Ensures the keyInRange method decodes a string representation of a key
        correctly, before testing if it's within range.
        """
        rangeMin = 1
        rangeMax = 66
        bucket = KBucket(rangeMin, rangeMax)
        self.assertTrue(bucket.keyInRange('A'))

    def testLen(self):
        """
        Ensures the number of nodes in the k-bucket is returned by __len__.
        """
        rangeMin = 12345
        rangeMax = 98765
        bucket = KBucket(rangeMin, rangeMax)
        contact = Contact("12345", "192.168.0.2", 8888, 123)
        bucket.addContact(contact)
        self.assertEqual(1, len(bucket))
