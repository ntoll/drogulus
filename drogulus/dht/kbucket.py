"""
Defines contact related storage (the so called k-buckets).

Copyright (C) 2012 Nicholas H.Tollervey.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from constants import K


class KBucketFull(Exception):
    """ Raised when the bucket is full """
    pass


class KBucket(object):
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
    """

    def __init__(self, rangeMin, rangeMax):
        """
        @param rangeMin: The lower bound of the k-bucket's 160-bit ID space.
        @param rangeMax: The upper bound of the k-bucket's 160-bit ID space.
        """
        self.rangeMin = rangeMin
        self.rangeMax = rangeMax
        self._contacts = []

    def addContact(self, contact):
        """
        Adds a contact to the k-bucket. If this is a new contact then it will
        be appended to the _contacts list. If the contact is already in the
        k-bucket then it is moved to the end of the _contacts list. The most
        recently seen contact is always at the end of the _contacts list. If
        the size of the k-bucket exceeds the constant k then a KBucketFull
        exception is raised.
        """
        if contact in self._contacts:
            self._contacts.remove(contact)
            self._contacts.append(contact)
        elif len(self._contacts) < K:
            self._contacts.append(contact)
        else:
            raise KBucketFull("No space in bucket to insert contact.")

    def getContact(self, id):
        """
        Returns a contact stored in the k-bucket with the given id. Will raise
        a ValueError if the contact is not in the k-bucket (the default
        behaviour of calling ``index`` with a value that's not in the list).
        """
        index = self._contacts.index(id)
        return self._contacts[index]

    def removeContact(self, id):
        """
        Removes a contact with the given id from the k-bucket.
        """
        self._contacts.remove(id)

    def keyInRange(self, key):
        """
        Checks if a key is within the range covered by this k-bucket. Indicates
        if a certain key should be places within this k-bucket.
        """
        if isinstance(key, str):
           key = long(key.encode('hex'), 16)
        return self.rangeMin <= key < self.rangeMax

    def __len__(self):
        """
        Returns the number of contacts stored in this k-bucket.
        """
        return len(self._contacts)
