"""
Contains code that defines the local node in the DHT network.
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

from twisted.internet import reactor, defer
import twisted.internet.threads

import constants
from routingtable import RoutingTable
from datastore import DictDataStore
from net import TimeoutError, DHTProtocol
from contact import Contact


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network by a client application are
    performed via this class (or a subclass).
    """

    def __init__(self, id=None):
        self.id = id
        self._routing_table = RoutingTable(id)
        self._data_store = DictDataStore

    def joinNetwork(self, seedNodes=None):
        """
        Causes the Node to join the DHT network. This should be called before
        any other DHT operations. The seedNodes argument contains a list of
        tuples describing existing nodes on the network in the form of their
        ID address and port.
        """
        pass

    def ping(self):
        """
        """
        pass

    def store(self, key, value):
        """
        """
        pass

    def findNode(self, key):
        """
        """
        pass

    def findValue(self, key):
        """
        """
        pass
