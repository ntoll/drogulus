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

from dht import node
from constants import DUPLICATION_COUNT


class Drogulus(object):
    """
    Represents a node in the Drogulus distributed hash table. This is the
    class that should generally be instantiated.
    """

    def __init__(self, alias=None):
        self._node = node()
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
        pass

    def set(self, key_name, value, duplicate=DUPLICATION_COUNT, meta=None,
            expires=None):
        """
        Stores a value at a compound key made from the local node's public key
        and the passed in meaningful key name. Returns a deferred that fires
        when the value has been stored to duplicate number of nodes. An
        optional meta dictionary and expires timestamp can also be specified.
        """
        pass
