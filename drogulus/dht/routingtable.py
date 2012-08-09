"""
Contains code that represents Kademlia's routing table tree structure.

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

import time, random

import constants
import kbucket
from net import TimeoutError


class RoutingTable(object):
    """
    From the original paper:

    "The routing table is a binary tree whose leaves are k-buckets. Each
    k-bucket contains nodes with some common prefic in their ID. The prefix is
    the k-bucket's position in the the binary tree. Thus, each k-bucket covers
    some range of the ID space, and together the k-buckets cover the entire
    160-bit ID space with no overlap."
    """

    def __init__(self, parentNodeID):
        """
        The parentNodeID is the 160-bit ID of the node to which this routing
        table belongs.
        """
        # Create the initial (single) k-bucket covering the range of the
        # entire 160-bit ID space
        self._buckets = [kbucket.KBucket(rangeMin=0, rangeMax=2**160)]
        self._parentNodeID = parentNodeID
        # Cache containing nodes eligible to replace stale k-bucket entries
        self._replacementCache = {}

    def _kbucketIndex(self, key):
        """
        Returns the index of the k-bucket responsible for the specified key
        string.
        """
        if isinstance(key, str):
            key = long(key.encode('hex'), 16)
        i = 0
        for bucket in self._buckets:
            if bucket.keyInRange(key):
                return i
            else:
                i += 1
        return i

    def _randomKeyInBucketRange(self, bucketIndex):
        """
        Returns a random key in the specified k-bucket's range.
        """
        keyValue = random.randrange(self._buckets[bucketIndex].rangeMin,
            self._buckets[bucketIndex].rangeMax)
        randomKey = hex(keyValue)[2:]
        if randomKey[-1] == 'L':
            randomKey = randomKey[:-1]
        if len(randomKey) % 2 != 0:
            randomKey = '0' + randomKey
        randomKey = randomKey.decode('hex')
        randomKey = (20 - len(randomKey))*'\x00' + randomKey
        return randomKey

    def _splitBucket(self, oldBucketIndex):
        """
        Splits the specified k-bucket into two new buckets which together
        cover the same range in the key/ID space.
        """
        # Resize the range of the current (old) k-bucket.
        oldBucket = self._buckets[oldBucketIndex]
        splitPoint = oldBucket.rangeMax - (
            oldBucket.rangeMax - oldBucket.rangeMin)/2
        # Create a new k-bucket to cover the range split off from the old
        # bucket.
        newBucket = kbucket.KBucket(splitPoint, oldBucket.rangeMax)
        oldBucket.rangeMax = splitPoint
        # Now, add the new bucket into the routing table tree.
        self._buckets.insert(oldBucketIndex + 1, newBucket)
        # Finally, copy all nodes that belong to the new k-bucket into it...
        for contact in oldBucket._contacts:
            if newBucket.keyInRange(contact.id):
                newBucket.addContact(contact)
        # ...and remove them from the old bucket
        for contact in newBucket._contacts:
            oldBucket.removeContact(contact)

    def addContact(self, contact):
        """
        Add the given contact to the correct k-bucket; if it already exists,
        its status will be updated.
        """
        if contact.id == self._parentNodeID:
            return

        # Initialize/reset the "failed RPC" counter since adding it to the
        # routing table is the result of a successful RPC.
        contact.failedRPCs = 0

        bucketIndex = self._kbucketIndex(contact.id)
        try:
            self._buckets[bucketIndex].addContact(contact)
        except kbucket.KBucketFull:
            # The bucket is full; see if it can be split (by checking if its
            # range includes the host node's id)
            if self._buckets[bucketIndex].keyInRange(self._parentNodeID):
                self._splitBucket(bucketIndex)
                # Retry the insertion attempt
                self.addContact(contact)
            else:
                # We can't split the k-bucket
                # NOTE: This implementation follows section 4.1 of the 13 page
                # version of the Kademlia paper (optimized contact accounting
                # without PINGs - results in much less network traffic, at the
                # expense of some memory)

                # Put the new contact in our replacement cache for the
                # corresponding k-bucket (or update it's position if it exists
                # already).
                if not self._replacementCache.has_key(bucketIndex):
                    self._replacementCache[bucketIndex] = []
                if contact in self._replacementCache[bucketIndex]:
                    self._replacementCache[bucketIndex].remove(contact)
                elif len(self._replacementCache[bucketIndex]) >= constants.K:
                    # Use k to limit the size of the contact replacement cache.
                    self._replacementCache[bucketIndex].pop(0)
                self._replacementCache[bucketIndex].append(contact)

    def distance(self, keyOne, keyTwo):
        """
        Calculate the XOR result between two string variables returned as a
        long type value.
        """
        valKeyOne = long(keyOne.encode('hex'), 16)
        valKeyTwo = long(keyTwo.encode('hex'), 16)
        return valKeyOne ^ valKeyTwo

    def findCloseNodes(self, key, count, rpcNodeID=None):
        """
        Finds a "count" number of known nodes closest to the node/value with
        the specified key. If _rpcNodeID is supplied the referenced node will
        be excluded from the returned contacts.

        The result is a list of length "count" of node contacts of type
        dht.contact.Contact. If will only return fewer contacts if they are all
        of the contacts that it knows of.
        """

    def getContact(self, contactID):
        """
        Returns the (known) contact with the specified node ID. Will raise
        a ValueError if no contact with eth specified ID is known.
        """

    def getRefreshList(self, startIndex=0, force=False):
        """
        Finds all k-buckets that need refreshing, starting at the
        k-bucket with the specified index. This bucket and those further away
        from it will be refreshed. Returns node IDs to be searched for
        in order to refresh those k-buckets in the routing table. If the
        "force" parameter is True then all buckets with the specified range
        will be refreshed, regardless of the time they were last accessed.
        """

    def removeContact(self, contactID):
        """
        Remove the contact with the specified contactID string from the
        routing table.
        """

    def touchKBucket(self, key):
        """
        Update the "last accessed" timestamp of the k-bucket which covers
        the range containing the specified key string in the key/ID space.
        """
