# -*- coding: utf-8 -*-
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

from twisted.python import log
import time

import constants
from messages import (Error, Ping, Pong, Store, FindNode, Nodes, FindValue,
                      Value)
from routingtable import RoutingTable
from datastore import DictDataStore
from contact import Contact
from crypto import validate_message
from drogulus.version import get_version


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network by a client application are
    performed via this class (or a subclass).
    """

    def __init__(self, id):
        """
        Initialises the object representing the node with the given id.
        """
        self.id = id
        self._routing_table = RoutingTable(id)
        self._data_store = DictDataStore()
        self.version = get_version()
        log.msg('Initialised node with id: %r' % self.id)

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
        log.msg('Message received from %s' % other_node)
        log.msg(message)
        self._routing_table.add_contact(other_node)
        # Sort on message type and pass to handler method.
        if isinstance(message, Ping):
            self.handle_ping(message, protocol)
        elif isinstance(message, Store):
            self.handle_store(message, protocol, other_node)
        elif isinstance(message, FindNode):
            self.handle_find_node(message, protocol)
        elif isinstance(message, FindValue):
            self.handle_find_value(message, protocol)
        elif isinstance(message, Error):
            self.handle_error(message, protocol, other_node)

    def handle_ping(self, message, protocol):
        """
        Handles an incoming Ping message. Returns a Pong message using the
        referenced protocol object.
        """
        pong = Pong(message.uuid, self.id, self.version)
        protocol.sendMessage(pong, True)

    def handle_store(self, message, protocol, sender):
        """
        Handles an incoming Store message. Checks the provenance of the
        message before storing locally. If there is a problem, removes the
        untrustworthy peer from the routing table.

        Sends a Pong message if successful otherwise replies with an Error.
        """
        # Check provenance
        is_valid, err_code = validate_message(message)
        if is_valid:
            # Store value.
            self._data_store.set_item(message.key, message)
            # Reply with a pong so the other end updates its routing table.
            pong = Pong(message.uuid, self.id, self.version)
            protocol.sendMessage(pong, True)
        else:
            # Remove from the routing table.
            log.msg('Problem with Store command: %d - %s' %
                    (err_code, constants.ERRORS[err_code]))
            self._routing_table.remove_contact(sender.id, True)
            details = {
                'message': 'You have been removed from remote routing table.'
            }
            err = Error(message.uuid, self.id, err_code,
                        constants.ERRORS[err_code], details, self.version)
            log.msg('Replying with Error message:')
            log.msg(err)
            protocol.sendMessage(err, True)

    def handle_find_node(self, message, protocol):
        """
        Handles an incoming FindNode message. Finds the details of up to K
        other nodes closer to the target key that *this* node knows about.
        Responds with a "Nodes" message containing the list of matching
        nodes.
        """
        target_key = message.key
        # List containing tuples of information about the matching contacts.
        other_nodes = [(n.id, n.address, n.port, n.version) for n in
                       self._routing_table.find_close_nodes(target_key)]
        result = Nodes(message.uuid, self.id, other_nodes, self.version)
        protocol.sendMessage(result, True)

    def handle_find_value(self, message, protocol):
        """
        Handles an incoming FindValue message. If the local node contains the
        value associated with the requested key replies with an appropriate
        "Value" message. Otherwise, responds with details of up to K other
        nodes closer to the target key that the local node knows about. In
        this case a "Nodes" message containing the list of matching nodes is
        sent to the caller.
        """
        match = self._data_store.get(message.key, False)
        if match:
            result = Value(message.uuid, self.id, match.key, match.value,
                           match.timestamp, match.expires, match.public_key,
                           match.name, match.meta, match.sig, match.version)
            protocol.sendMessage(result, True)
        else:
            self.handle_find_node(message, protocol)

    def handle_error(self, message, protocol, sender):
        """
        Handles an incoming Error message. Currently, this simply logs the
        error and closes the connection. In future this *may* remove the
        sender from the routing table (depending on the error).
        """
        log.msg('***** ERROR ***** from %s' % sender)
        log.msg(message)

    def handle_value(self, message, sender):
        """
        Handles an incoming Value message containing a value retrieved from
        another node on the DHT. Ensures the message is valid and calls the
        referenced deferred to signal the arrival of the value.

        TODO: How to handle invalid messages and errback the deferred.
        """
        pass

    def handle_nodes(self, message):
        """
        """
        pass
