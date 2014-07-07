# -*- coding: utf-8 -*-
"""
Buckets in the routing table that contain peer nodes.
"""
from .constants import K
from .errors import BucketFull


class Bucket(object):
    """
    A bucket to store contact information about other nodes in the network.
    From the original Kademlia paper:

    "Kademlia nodes store contact information about each other to route query
    messages. For each 0 <= i < 160, every node keeps a list of <IP address,
    port, Node ID> triples for nodes of distance between 2i and 2(i+1) from
    itself. We call these lists k-buckets. Each k-bucket is kept sorted by time
    last seen -- least-recently seen node at the head, most-recently seen at
    the tail. For small values of i, the k-buckets will generally be empty (as
    no appropriate nodes will exist). For large values of i, the lists can
    grow to size k, where k is a system-wide replication parameter. k is
    chosen such that any given k nodes are very unlikely to fail within an
    hour of each other (for example k = 20)"

    Nota Bene: This implementation of Kademlia uses a 512 bit key space
    based upon SHA512 rather than the original 160 bit SHA1 implementation, so
    i will be < 512.

    The keys stored within a bucket are integer values derived from the
    hexdigest of sha512 hashes.
    """

    def __init__(self, range_min, range_max):
        """
        Initialises the object with the lower / upper bound limits of the
        bucket's 512-bit ID space.
        """
        self.range_min = range_min
        self.range_max = range_max
        # Holds the contacts contained within the bucket.
        self._contacts = []
        # Indicates when the bucket was last accessed. Used to make sure the
        # bucket doesn't become stale and out of date given changing
        # conditions in the network of contacts.
        self.last_accessed = 0

    def add_contact(self, contact):
        """
        Adds a contact to the bucket. If this is a new contact then it will
        be appended to the _contacts list. If the contact is already in the
        bucket then it is moved to the end of the _contacts list. The most
        recently seen contact is always at the end of the _contacts list. If
        the size of the bucket exceeds the constant k then a BucketFull
        exception is raised.
        """
        if contact in self._contacts:
            self._contacts.remove(contact)
            self._contacts.append(contact)
        elif len(self._contacts) < K:
            self._contacts.append(contact)
        else:
            raise BucketFull("No space in bucket to insert contact.")

    def get_contact(self, key):
        """
        Returns a contact stored in the bucket with the given key. Will
        raise a ValueError if the contact is not in the bucket (the default
        behaviour of calling ``index`` with a value that's not in the list).
        """
        index = self._contacts.index(key)
        return self._contacts[index]

    def get_contacts(self, count=0, exclude_contact=None):
        """
        Returns a list of up to "count" number of contacts within the
        bucket. If "count" is zero or less, then all contacts will be
        returned. If there are less than "count" number of contacts in the
        bucket, all contacts will be returned.

        If "exclude_contact" is passed (as either a PeerNode instance or id
        str) then, if this is found within the list of returned values, it
        will be discarded before the result is returned.
        """
        current_len = len(self._contacts)
        if count <= 0:
            count = current_len

        if not self._contacts:
            contact_list = []
        elif current_len < count:
            contact_list = self._contacts[:current_len]
        else:
            contact_list = self._contacts[:count]

        if exclude_contact in contact_list:
            contact_list.remove(exclude_contact)
        return contact_list

    def remove_contact(self, key):
        """
        Removes a contact with the given key from the bucket.
        """
        self._contacts.remove(key)

    def key_in_range(self, key):
        """
        Checks if a key is within the range covered by this bucket. Returns
        a boolean to indicate if a certain key should be placed within this
        bucket. The key is expressed as the hexdigest of a sha512.
        """
        if isinstance(key, str):
            key = int(key, 16)
        return self.range_min <= key < self.range_max

    def __len__(self):
        """
        Returns the number of contacts stored in this bucket.
        """
        return len(self._contacts)
