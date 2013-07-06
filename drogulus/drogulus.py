# -*- coding: utf-8 -*-
"""
Encapsulates a node in the drogulus.
"""

# Copyright (C) 2012-2013 Nicholas H.Tollervey.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from constants import DUPLICATION_COUNT, EXPIRY_DURATION
from crypto import generate_signature, construct_key
from dht.node import Node


class Drogulus(object):
    """
    Represents a node in the Drogulus distributed hash table. This is the
    class that generally should be instantiated.
    """

    def __init__(self, private_key, public_key, alias=None):
        self.private_key = private_key
        self.public_key = public_key
        self._node = Node()
        if alias:
            self.alias = alias
        else:
            self.alias = {}

    def join(self):
        """
        Causes the node to join the distributed hash table. Returns a deferred
        that fires when the operation is complete.
        """
        pass

    def whois(self, public_key):
        """
        Given the public key of an entity that uses the drogulus will return a
        deferred that fires when information about them stored in the DHT is
        retrieved.
        """
        return self.get(public_key, None)

    def get(self, public_key, key_name):
        """
        Gets the value associated with a compound key made of the passed in
        public key and meaningful key name. Returns a deferred that fires when
        the value is retrieved.
        """
        target = construct_key(public_key, key_name)
        return self._node.retrieve(target)

    def set(self, key_name, value, duplicate=DUPLICATION_COUNT, meta=None,
            expires=EXPIRY_DURATION):
        """
        Stores a value at a compound key made from the local node's public key
        and the passed in meaningful key name. Returns a deferred that fires
        when the value has been stored to duplicate number of nodes. An
        optional meta dictionary and expires duration (to be added to the
        current time) can also be specified.
        """
        timestamp = time.time()

        if meta is None:
            meta = {}

        if expires < 1:
            expires = -1
        else:
            expires = timestamp + expires

        signature = generate_signature(value, timestamp, expires, key_name,
                                       meta, self.private_key)

        return self._node.replicate(self.public_key, key_name, value,
                                    timestamp, expires, meta, signature,
                                    duplicate)
