"""
Contains class definitions that define the local data store for the node.
"""

# Copyright (C) 2012 Nicholas H.Tollervey.
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

import UserDict
import time


class DataStore(UserDict.DictMixin):
    """
    Base class for implementations of the storage mechanism for the DHT.
    """

    def keys(self):
        """
        Return a list of the keys in this data store.
        """
        return NotImplemented

    def last_published(self, key):
        """
        Get the time that a key/value pair identified by the key were last
        published.
        """
        return NotImplemented

    def original_publisher_id(self, key):
        """
        Get the node ID of the original publisher of the key/value pair
        identified by "key".
        """
        return NotImplemented

    def original_publish_time(self, key):
        """
        Get the time that key was originally published.
        """
        return NotImplemented

    def set_item(self, key, value):
        """
        Set the value of the key/value pair identified by "key"; this should
        set the "last published" value for the key/value pair to the current
        time.
        """
        return NotImplemented

    def __getitem__(self, key):
        """
        Get the value identified by "key".
        """
        return NotImplemented

    def __setitem__(self, key, value):
        """
        Convenience wrapper to setItem. This accepts a tuple of the format:
        (value, lastPublished, originallyPublished, originalPublisherID).
        """
        self.set_item(key, value)

    def __delitem__(self, key):
        """
        Delete the specified key and associated value.
        """
        raise KeyError()


class DictDataStore(DataStore):
    """
    A datastore using Python's in-memory dictionary.
    """

    def __init__(self):
        self._dict = {}

    def keys(self):
        """
        Return a list of the keys in this data store.
        """
        return self._dict.keys()

    def last_published(self, key):
        """
        Get the time the key/value pair identified by key was last published.
        """
        return self._dict[key][1]

    def original_publisher_id(self, key):
        """
        Get the original publisher of the data's node ID.
        """
        return self._dict[key][0].public_key

    def original_publish_time(self, key):
        """
        Get the time the key/value pair identified by key was originally
        published
        """
        return self._dict[key][0].timestamp

    def set_item(self, key, value):
        """
        Set the value of the key/value pair identified by key.
        """
        lastPublished = time.time()
        self._dict[key] = (value, lastPublished)

    def __getitem__(self, key):
        """
        Get the value identified by key.
        """
        return self._dict[key][0]

    def __delitem__(self, key):
        """
        Delete the specified key (and its value)
        """
        del self._dict[key]
