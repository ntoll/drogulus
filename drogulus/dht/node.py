# -*- coding: utf-8 -*-
"""
Contains code that defines the local node in the DHT network.
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

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.internet.endpoints import clientFromString
import time

from drogulus import constants
from drogulus.net.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value)
from routingtable import RoutingTable
from datastore import DictDataStore
from contact import Contact
from drogulus.crypto import validate_message
from drogulus.version import get_version


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network by a client application are
    performed via this class (or a subclass).
    """

    def __init__(self, id, client_string='ssl:%s:%d:'):
        """
        Initialises the object representing the node with the given id.
        """
        # The node's ID within the distributed hash table.
        self.id = id
        # The routing table stores information about other nodes on the DHT.
        self._routing_table = RoutingTable(id)
        # The local key/value store containing data held by this node.
        self._data_store = DictDataStore()
        # A dictionary of IDs for messages pending a response and associated
        # deferreds to be fired when a response is completed.
        self._pending = {}
        # The template string to use when initiating a connection to another
        # node on the network.
        self._client_string = client_string
        # The version of Drogulus that this node implements.
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
        # Sort on message type and pass to handler method. Explicit > implicit.
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
            # Ensure the node doesn't already have a more up-to-date version
            # of the value.
            current = self._data_store.get(message.key, False)
            if current and (message.timestamp < current.timestamp):
                # The node already has a later version of the value so
                # return an error.
                details = {
                    'new_timestamp': '%d' % current.timestamp
                }
                raise ValueError(8, constants.ERRORS[8], details,
                                 message.uuid)
            # Good to go, so store value.
            self._data_store.set_item(message.key, message)
            # Reply with a pong so the other end updates its routing table.
            pong = Pong(message.uuid, self.id, self.version)
            protocol.sendMessage(pong, True)
        else:
            # Remove from the routing table.
            log.msg('Problem with Store command: %d - %s' %
                    (err_code, constants.ERRORS[err_code]))
            self._routing_table.remove_contact(sender.id, True)
            # Return an error.
            details = {
                'message': 'You have been removed from remote routing table.'
            }
            raise ValueError(err_code, constants.ERRORS[err_code], details,
                             message.uuid)

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
        # TODO: Handle error 8 (out of date data)
        log.msg('***** ERROR ***** from %s' % sender)
        log.msg(message)

    def handle_value(self, message, sender):
        """
        Handles an incoming Value message containing a value retrieved from
        another node on the DHT. Ensures the message is valid and calls the
        referenced deferred to signal the arrival of the value.

        TODO: How to handle invalid messages and errback the deferred.
        """
        d.callback(foo)
        pass

    def handle_nodes(self, message):
        """
        Handles an incoming Nodes message containing information about other
        nodes on the network that are close to a requested key.
        """
        d.callback(foo)
        pass

    def timeout(self, uuid, protocol):
        """
        Called when a pending message awaiting a response times-out. Cleans
        up the _pending dict correctly.
        """
        # TODO: Close connection and clean up protocol object.
        del self._pending[uuid]

    def send_message(self, contact, message):
        """
        Abstracts the sending of a message to the specified contact, adds it
        to the _pending dictionary and ensures it times-out after the correct
        period.
        """
        d = defer.Deferred()
        # open network call.
        client_string = self._client_string % (contact.address, contact.port)
        client = clientFromString(reactor, client_string)
        connected = client.connect(DHTFactory(self))

        def on_connect(protocol):
            # TODO: self???
            protocol.sendMessage(message)
            self._pending[message.uuid] = d
            reactor.callLater(constants.RPC_TIMEOUT, self.timeout, self,
                              message.uuid, protocol)

        connected.addCallback(on_connect)
        # TODO: Add errBack
        return d

    def send_ping(self, contact):
        """
        Sends a ping request to the given contact and returns a deferred
        that is fired when the reply arrives or an error occurs.
        """
        pass

    def send_store(self, contact, public_key, name, value, timestamp, expires,
                   meta):
        """
        Sends a Store message to the given contact. The value contained within
        the message is stored against a key derived from the public_key and
        name. Furthermore, the message is cryptographically signed using the
        value, timestamp, expires, name and meta values.
        """
        pass

    def send_find_node(self, contact, id):
        """
        Sends a FindNode message to the given contact with the intention of
        obtaining contact information about the node with the specified id.
        """
        pass

    def send_find_value(self, contact, key):
        """
        Sends a FindValue message to the given contact with the intention of
        obtaining the value associated with the specified key.
        """
        pass
