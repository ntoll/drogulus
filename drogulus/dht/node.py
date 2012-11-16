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
from uuid import uuid4
import time

import constants
from messages import (Error, Ping, Pong, Store, FindNode, Nodes, FindValue,
                      Value)
from routingtable import RoutingTable
from datastore import DictDataStore
from net import TimeoutError, DHTProtocol
from contact import Contact
from constants import ERRORS
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

    def except_to_error(self, exception):
        """
        Given a Python exception will return an appropriate Error message
        instance.
        """
        node = self.id
        version = get_version()
        if isinstance(exception, Exception) and len(exception.args) == 4:
            # Exception includes all the information we need.
            uuid = exception.args[3]
            code = exception.args[0]
            title = exception.args[1]
            details = exception.args[2]
        else:
            uuid = str(uuid4())
            code = 3
            title = ERRORS[code]
            details = {}
        return Error(uuid, node, code, title, details, version)

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
        # Update the routing table.
        peer = protocol.transport.getPeer()
        other_node = Contact(message.node, peer.host, peer.port,
                             message.version, time.time())
        self._routing_table.add_contact(other_node)
        # Sort on message type and pass to handler method.
        if isinstance(message, Ping):
            self.handle_ping(message, protocol)

    def handle_ping(self, message, protocol):
        """
        Handles an incoming Ping message
        """
        pong = Pong(message.uuid, self.id, self.version)
        protocol.sendMessage(pong, True)

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
