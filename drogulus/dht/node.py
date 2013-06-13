# -*- coding: utf-8 -*-
"""
Contains code that defines the behaviour of the local node in the DHT network.
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
from uuid import uuid4

from drogulus import constants
from drogulus.net.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value)
from drogulus.net.protocol import DHTFactory
from routingtable import RoutingTable
from datastore import DictDataStore
from contact import Contact
from drogulus.crypto import validate_message, construct_key, generate_signature
from drogulus.version import get_version


class RoutingTableEmpty(Exception):
    """
    Fired when a lookup is attempted without any peers in the local node's
    routing table.
    """
    pass


def response_timeout(message, protocol, node):
    """
    Called when a pending message (identified with a uuid) awaiting a response
    via a given protocol object times-out. Closes the connection and removes
    the deferred from the "pending" dictionary.
    """
    uuid = message.uuid
    pending = node._pending
    if uuid in pending:
        pending[uuid].cancel()
        del pending[uuid]
        protocol.transport.abortConnection()
        node._routing_table.remove_contact(message.node)


class NodeLookup(defer.Deferred):
    """
    Encapsulates a lookup in the DHT given a particular target key and message
    type. Will callback when a result is found or errback otherwise. If
    defined, will timeout with an errback.

    From the original Kademlia paper:

    "The most important procedure a Kademlia participant must perform is to
    locate the k closest nodes to some given node ID. We call this procedure a
    node lookup. Kademlia employs a recursive algorithm for node lookups. The
    lookup initiator starts by picking α nodes from its closest non-empty
    k-bucket (or, if that bucket has fewer than α entries, it just takes the α
    closest nodes it knows of). The initiator then sends parallel, asynchronous
    FIND NODE RPCs to the α nodes it has chosen. α is a system-wide concurrency
    parameter, such as 3.

    In the recursive step, the initiator resends the FIND NODE to nodes it has
    learned about from previous RPCs. (This recursion can begin before all α of
    the previous RPCs have returned). Of the k nodes the initiator has heard of
    closest to the target, it picks α that it has not yet queried and resends
    the FIND NODE RPC to them. Nodes that fail to respond quickly are removed
    from consideration until and unless they do respond. If a round of FIND
    NODEs fails to return a node any closer than the closest already seen, the
    initiator resends the FIND NODE to all of the k closest nodes it has not
    already queried. The lookup terminates when the initiator has queried and
    gotten responses from the k closest nodes it has seen. When α = 1 the
    lookup algorithm resembles Chord’s in terms of message cost and the latency
    of detecting failed nodes. However, Kademlia can route for lower latency
    because it has the flexibility of choosing any one of k nodes to forward a
    request to."

    READ THIS CAREFULLY! Here's how this implementation works:

    self.target - the target key for the lookup.
    self.message_type - the message class (either FindNode or FindValue).
    self.local_node - the local node that created the NodeLookup.
    self.shortlist - an ordered list containing nodes close to the target.
    self.contacted - a set of nodes that have been contacted for this lookup.
    self.nearest_node - the node nearest to the target so far.
    self.pending_requests - a dictionary of currently pending requests.
    constants.ALPHA - the number of concurrent asynchronous calls allowed.
    constants.K - the number of closest nodes to return when complete.
    constants.LOOKUP_TIMEOUT - the default maximum duration for a lookup.

    0. If "timeout" number of seconds elapse before the lookup is finished then
       cancel any pending requests and errback with an OutOfTime error. The
       "timeout" value can be overridden but defaults to
       constants.LOOKUP_TIMEOUT seconds.

    1. Locally known nodes from the routing table seed self.shortlist.

    2. The nearest node to the target in self.shortlist is set as
       self.nearest_node.

    3. No more than constants.ALPHA nearest nodes that are in self.shortlist
       but not in self.contacted are sent a message that is an instance of
       self.message_type. Each request is added to the self.pending_requests
       list. The length of self.pending_requests must never be more than
       constants.ALPHA.

    4. As each node is contacted it is added to the self.contacted set.

    5. If a node doesn't reply or an error is encountered it is removed from
       self.shortlist and self.pending_requests. Start from step 3 again.

    6. When a response to a request is returned successfully remove the request
       from self.pending_requests.

    7. If it's a FindValue message and a suitable value is returned (see note
       at the end of these comments) cancel all the other pending calls in
       self.pending_requests and fire a callback with with the returned value.
       If the value is invalid remove the node from self.shortlist and start
       from step 3 again without cancelling the other pending calls.

    8. If a list of closer nodes is returned by a peer add them to
       self.shortlist and sort - making sure nodes in self.contacted are not
       mistakenly re-added to the shortlist.

    7. If the nearest node in the newly sorted self.shortlist is closer to the
       target than self.nearest_node then set self.nearest_node to the new
       closer node and start from step 3 again.

    8. If self.nearest_node remains unchanged DO NOT start a new call.

    9. If there are no other requests in self.pending_requests then check that
       the constants.K nearest nodes in the self.contacted set are all closer
       than the nearest node in self.shortlist. If they are, and it's a
       FindNode message call back with the constants.K nearest nodes in the
       self.contacted set. If the message is a FindValue, errback with a
       ValueNotFound error.

    10. If there are still nearer nodes in self.shortlist to some of those in
        the constants.K nearest nodes in the self.contacted set then start
        from step 3 again.

    Note on validating values: In the future there may be constraints added to
    the FindValue query (such as only accepting values created after time T).
    """

    def __init__(self, target, message_type, local_node,
                 timeout=constants.LOOKUP_TIMEOUT, canceller=None):
        """
        Sets up the lookup to search for a certain target key with a particular
        message_type using the DHT state found in the local_node. Will cancel
        after timeout seconds. See the documentation for
        twisted.internet.defer.Deferred for explanation of canceller.
        """
        defer.Deferred.__init__(self, canceller)
        self.target = target
        self.message_type = message_type
        self.local_node = local_node
        # A set of nodes that have been contacted for this lookup.
        self.contacted = set()
        # Holds currently pending requests.
        self.pending_requests = {}
        if timeout:
            reactor.callLater(timeout, self.cancel)
        # To hold peers in the DHT that are known to the local node that are
        # possibly close to the target key. Closest nodes come first.
        self.shortlist = self.local_node._routing_table.\
            find_close_nodes(target)
        if self.target != self.local_node.id:
            # Update the last_accessed attribute of the affected k-bucket.
            self.local_node._routing_table.touch_kbucket(target)
        if not self.shortlist:
            # The node knows of no other nodes within the DHT.
            self.errback(RoutingTableEmpty())
            return
        # Holds the currently closest node to the target.
        self.nearest_node = self.shortlist[0]
        # Start the lookup process
        self._lookup()

    def _cancel_pending_requests(self):
        """
        Causes the deferreds waiting on pending requests to be cancelled in
        a clean fashion.
        """
        requests = self.pending_requests.values()
        for request in requests:
            request.cancel()
        self.pending_requests = {}

    def cancel(self):
        """
        Cancels this lookup in a clean fashion. This function is dedicated to
        @terrycojones whose efforts at cancelling deferreds deserve some sort
        of tribute. ;-)
        """
        self._cancel_pending_requests()
        defer.Deferred.cancel(self)

    def _handle_error(self, uuid, contact, error):
        """
        Callback to handle error conditions.

        If a node doesn't reply or an error is encountered it is removed from
        self.shortlist and self.pending_requests. Start the _lookup again.
        """
        if contact in self.shortlist:
            self.shortlist.remove(contact)
        if uuid in self.pending_requests:
            del self.pending_requests[uuid]
        self._lookup()

    def _handle_response(self, uuid, contact, response):
        """
        Callback to handle expected results.

        When a response to a request is returned successfully remove the
        request from self.pending_requests.

        If it's a FindValue message and a suitable value is returned (see note
        at the end of these comments) cancel all the other pending calls in
        self.pending_requests and fire a callback with with the returned value.
        If the value is invalid remove the node from self.shortlist and start
        from step 3 again without cancelling the other pending calls.

        If a list of closer nodes is returned by a peer add them to
        self.shortlist and sort - making sure nodes in self.contacted are not
        mistakenly re-added to the shortlist.

        If the nearest node in the newly sorted self.shortlist is closer to the
        target than self.nearest_node then set self.nearest_node to the new
        closer node and start from step 3 again.

        If self.nearest_node remains unchanged DO NOT start a new call.

        If there are no other requests in self.pending_requests then check that
        the constants.K nearest nodes in the self.contacted set are all closer
        than the nearest node in self.shortlist. If they are, and it's a
        FindNode message call back with the constants.K nearest nodes in the
        self.contacted set. If the message is a FindValue, errback with a
        ValueNotFound error.

        If there are still nearer nodes in self.shortlist to some of those in
        the constants.K nearest nodes in the self.contacted set then start
        from step 3 again.
        """
        pass

    def _lookup(self):
        """
        Sends parallel lookup messages to the self.shortlist of contacts.

        No more than constants.ALPHA nearest nodes that are in self.shortlist
        but not in self.contacted are sent a message that is an instance of
        self.message_type. Each request is added to the self.pending_requests
        list. The length of self.pending_requests must never be more than
        constants.ALPHA.

        As each node is contacted it is added to the self.contacted set.
        """

        for contact in self.shortlist:
            if contact not in self.contacted:
                # Guard to ensure only ALPHA requests are ever active at any
                # one time
                if len(self.pending_requests) >= constants.ALPHA:
                    break

                uuid, deferred = self.local_node.send_find(contact,
                                                           self.target,
                                                           self.message_type)

                def callback(result):
                    """
                    Passes the result to the NodeLookup instance to handle.
                    """
                    self._handle_response(uuid, contact, result)

                def errback(error):
                    """
                    Passes the error to the NodeLookup instance to handle.
                    """
                    self._handle_error(uuid, contact, error)

                deferred.addCallbacks(callback, errback)
                self.pending_requests[uuid] = deferred
                self.contacted.add(contact)


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network by a client application are
    performed via this class (or a subclass).
    """

    def __init__(self, id, client_string='ssl:%s:%d'):
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

    def join(self, seed_nodes=None):
        """
        Causes the Node to join the DHT network. This should be called before
        any other DHT operations. The seedNodes argument contains a list of
        tuples describing existing nodes on the network in the form of their
        IP address and port.
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
        elif isinstance(message, Pong):
            self.handle_pong(message)
        elif isinstance(message, Store):
            self.handle_store(message, protocol, other_node)
        elif isinstance(message, FindNode):
            self.handle_find_node(message, protocol)
        elif isinstance(message, FindValue):
            self.handle_find_value(message, protocol)
        elif isinstance(message, Error):
            self.handle_error(message, protocol, other_node)
        elif isinstance(message, Value):
            self.handle_value(message, other_node)
        elif isinstance(message, Nodes):
            self.handle_nodes(message)

    def send_message(self, contact, message):
        """
        Sends a message to the specified contact, adds it to the _pending
        dictionary and ensures it times-out after the correct period. If an
        error occurs the deferred's errback is called.
        """
        d = defer.Deferred()
        # open network call.
        client_string = self._client_string % (contact.address, contact.port)
        client = clientFromString(reactor, client_string)
        connection = client.connect(DHTFactory(self))
        # Ensure the connection will potentially time out.
        connection_timeout = reactor.callLater(constants.RPC_TIMEOUT,
                                               connection.cancel)

        def on_connect(protocol):
            # Cancel pending connection_timeout if it's still active.
            if connection_timeout.active():
                connection_timeout.cancel()
            # Send the message and add a timeout for the response.
            protocol.sendMessage(message)
            self._pending[message.uuid] = d
            reactor.callLater(constants.RESPONSE_TIMEOUT, response_timeout,
                              message, protocol, self)

        def on_error(error):
            log.msg('***** ERROR ***** connecting to %s' % contact)
            log.msg(error)
            self._routing_table.remove_contact(message.node)
            d.errback(error)

        connection.addCallbacks(on_connect, on_error)
        return d

    def trigger_deferred(self, message, error=False):
        """
        Given a message, will attempt to retrieve the deferred and trigger it
        with the appropriate callback or errback.
        """
        if message.uuid in self._pending:
            deferred = self._pending[message.uuid]
            if error:
                error.message = message
                deferred.errback(error)
            else:
                deferred.callback(message)
            # Remove the called deferred from the _pending dictionary.
            del self._pending[message.uuid]

    def handle_ping(self, message, protocol):
        """
        Handles an incoming Ping message. Returns a Pong message using the
        referenced protocol object.
        """
        pong = Pong(message.uuid, self.id, self.version)
        protocol.sendMessage(pong, True)

    def handle_pong(self, message):
        """
        Handles an incoming Pong message.
        """
        self.trigger_deferred(message)

    def handle_store(self, message, protocol, sender):
        """
        Handles an incoming Store message. Checks the provenance and timeliness
        of the message before storing locally. If there is a problem, removes
        the untrustworthy peer from the routing table. Otherwise, at
        REPLICATE_INTERVAL minutes in the future, the local node will attempt
        to replicate the Store message elsewhere in the DHT if such time is
        <= the message's expiry time.

        Sends a Pong message if successful otherwise replies with an
        appropriate Error.
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
            # At some future time attempt to replicate the Store message
            # around the network IF it is within the message's expiry time.
            reactor.callLater(constants.REPLICATE_INTERVAL,
                              self.send_replicate, message)
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
        # Check provenance
        is_valid, err_code = validate_message(message)
        if is_valid:
            self.trigger_deferred(message)
        else:
            log.msg('Problem with incoming Value: %d - %s' %
                    (err_code, constants.ERRORS[err_code]))
            log.msg(message)
            # Remove the remote node from the routing table.
            self._routing_table.remove_contact(sender.id, True)
            error = ValueError(constants.ERRORS[err_code])
            self.trigger_deferred(message, error)

    def handle_nodes(self, message):
        """
        Handles an incoming Nodes message containing information about other
        nodes on the network that are close to a requested key.
        """
        self.trigger_deferred(message)

    def iterative_lookup(self, key, message_class):
        """
        A generic lookup function for finding nodes or values within the
        distributed hash table. Takes a key that either references a value or
        location in the hash-space. This function returns a deferred that will
        fire wth the found value or a set of peers in the DHT that are close to
        the key. The message class should be either FindNode or FindValue.
        """
        pass

    def send_ping(self, contact):
        """
        Sends a ping request to the given contact and returns a deferred
        that is fired when the reply arrives or an error occurs.
        """
        new_uuid = str(uuid4())
        ping = Ping(new_uuid, self.id, self.version)
        return self.send_message(contact, ping)

    def send_store(self, private_key, public_key, name, value,
                   timestamp, expires, meta):
        """
        Sends a Store message to the given contact. The value contained within
        the message is stored against a key derived from the public_key and
        name. Furthermore, the message is cryptographically signed using the
        value, timestamp, expires, name and meta values.
        """
        new_uuid = str(uuid4())
        signature = generate_signature(value, timestamp, expires, name, meta,
                                       private_key)
        compound_key = construct_key(public_key, name)
        new_store = Store(new_uuid, self.id, compound_key, value, timestamp,
                          expires, public_key, name, meta, signature,
                          self.version)
        return self.send_replicate(new_store)

    def send_replicate(self, store_message):
        """
        Sends an existing valid Store message (that will probably have
        originated from a third party) to another peer on the network for the
        purposes of replication / spreading popular values.
        """
        # Check for expiry time..?
        # Find closest node...
        """
        new_uuid = str(uuid4())
        store = Store(new_uuid, self.id, store_message.key,
                      store_message.value, store_message.timestamp,
                      store_message.expires, store_message.public_key,
                      store_message.name, store_message.meta,
                      store_message.sig, self.version)
        return self.send_message(contact, store)"""

    def send_find(self, contact, target, message_type):
        """
        Sends a Find[Node|Value] message to the given contact with the
        intention of obtaining information at the given target key. The type of
        find message is specified by message_type.
        """
        new_uuid = str(uuid4())
        find_message = message_type(new_uuid, self.id, target, self.version)
        deferred = self.send_message(contact, find_message)
        return (new_uuid, deferred)
