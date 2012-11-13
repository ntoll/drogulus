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
from messages import (Ping, Pong, Store, FindNode, Nodes, FindValue, Value,
                      except_to_error)
from routingtable import RoutingTable
from datastore import DictDataStore
from net import TimeoutError, DHTProtocol
from contact import Contact
from drogulus.version import get_version


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network by a client application are
    performed via this class (or a subclass).
    """

    def __init__(self, id=None):
        """
        Initialises the object representing the node with the given id.
        """
        self.id = id
        self._routing_table = RoutingTable(id)
        self._data_store = DictDataStore
        self.version = get_version()

    def join(self, seedNodes=None):
        """
        Causes the Node to join the DHT network. This should be called before
        any other DHT operations. The seedNodes argument contains a list of
        tuples describing existing nodes on the network in the form of their
        ID address and port.
        """
        pass

    def message_received(self, message, protocol):
        """
        Handles incoming messages.
        """
        # TODO: Update the routing table.
        # peer = protocol.transport.getPeer()
        if isinstance(message, Ping):
            self.handle_ping(message, protocol)

    def handle_ping(self, message, protocol):
        """
        Handles an incoming Ping message
        """
        pong = Pong(message.uuid, self.version)
        protocol.transport.sendMessage(pong)

    def handle_store(self, key, value):
        """
        """
        pass

    def handle_find_node(self, key):
        """
        """
        pass

    def handle_find_value(self, key):
        """
        """
        pass
