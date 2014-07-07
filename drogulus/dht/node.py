# -*- coding: utf-8 -*-
"""
Contains code that defines the behaviour of the local node in the DHT network.
"""
from .routingtable import RoutingTable
from .storage import DictDataStore
from .contact import PeerNode
from .crypto import check_seal
from .errors import BadMessage
from .messages import (Error, Ping, Pong, Store, FindNode, Nodes, FindValue,
                       Value)
from ..version import get_version
import logging
import time
from hashlib import sha512


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network are performed via this class (or a
    subclass).
    """

    def __init__(self, public_key, private_key, event_loop):
        """
        Initialises the object representing the node with the credentials.
        """
        self.public_key = public_key
        self.private_key = private_key
        self.event_loop = event_loop
        # The node's ID within the distributed hash table.
        self.network_id = sha512(public_key.encode('ascii')).hexdigest()
        # Reference to the event loop.
        self.event_loop = event_loop
        # The routing table stores information about other nodes on the DHT.
        self.routing_table = RoutingTable(self.network_id)
        # The local key/value store containing data held by this node.
        self.data_store = DictDataStore()
        # A dictionary of IDs for messages pending a response and associated
        # Future instances to be fired when a response is completed.
        self.pending = {}
        # The version of Drogulus that this node implements.
        self.version = get_version()
        logging.info('Initialised node with id: %r' % self.network_id)

    def join(self, seed_nodes=None):
        """
        Causes the Node to join the DHT network. This should be called before
        any other DHT operations. The seed_nodes argument must be a list of
        already known contacts describing existing nodes on the network.
        """
        if not seed_nodes:
            raise ValueError('Seed nodes required for node to join network')
        for contact in seed_nodes:
            self._routing_table.add_contact(contact)
        # Looking up the node's ID on the network will populate the routing
        # table with fresh nodes as well as tell us who our nearest neighbours
        # are.

        # TODO: Add callback to kick off refresh of k-buckets in future..?
        raise Exception('FIX ME!')
        # Ensure the refresh of k-buckets is set up properly.
        return (self.network_id, FindNode, self)

    def message_received(self, message, protocol, ip_address, port):
        """
        Handles incoming messages.
        """
        # Check the "seal" of the sender to make sure it's legit.
        if not check_seal(message):
            raise BadMessage()
        # Update the routing table.
        uri = '%s://%s:%d' % (protocol, ip_address, port)
        other_node = PeerNode(message.sender, message.version, uri,
                              time.time())
        logging.info('Message received from %s' % other_node)
        logging.info(message)
        self.routing_table.add_contact(other_node)
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
            log.msg('***** ERROR ***** interacting with %s' % contact)
            log.msg(error)
            self._routing_table.remove_contact(message.node)
            if message.uuid in self._pending:
                del self._pending[message.uuid]
            d.errback(error)

        connection.addCallback(on_connect)
        connection.addErrback(on_error)
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
                              self.republish, message)
        else:
            # Remove from the routing table.
            log.msg('Problem with Store command: %d - %s' %
                    (err_code, constants.ERRORS[err_code]))
            self._routing_table.blacklist(sender)
            # Return an error.
            details = {
                'message': 'You have been blacklisted.'
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
                           match.timestamp, match.expires, match.created_with,
                           match.public_key, match.name, match.meta, match.sig,
                           match.version)
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

    def send_ping(self, contact):
        """
        Sends a ping request to the given contact and returns a deferred
        that is fired when the reply arrives or an error occurs.
        """
        new_uuid = str(uuid4())
        ping = Ping(new_uuid, self.id, self.version)
        return self.send_message(contact, ping)

    def send_store(self, contact, public_key, name, value, timestamp, expires,
                   created_with, meta, signature):
        """
        Sends a Store message to the given contact. The value contained within
        the message is stored against a key derived from the public_key and
        name. Furthermore, the message is cryptographically signed using the
        value, timestamp, expires, name and meta values.
        """
        uuid = str(uuid4())
        compound_key = construct_key(public_key, name)
        store = Store(uuid, self.id, compound_key, value, timestamp, expires,
                      created_with, public_key, name, meta, signature,
                      self.version)
        return self.send_message(contact, store)

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

    def _process_lookup_result(self, nearest_nodes, public_key, name, value,
                               timestamp, expires, created_with, meta,
                               signature, length):
        """
        Given a list of nearest nodes will return a list of send_store based
        deferreds for the item to be stored in the DHT. The list will contain
        up to "length" number of deferreds.
        """
        list_of_deferreds = []
        for contact in nearest_nodes[:length]:
            deferred = self.send_store(contact, public_key, name, value,
                                       timestamp, expires, created_with,
                                       meta, signature)
            list_of_deferreds.append(deferred)
        return list_of_deferreds

    def replicate(self, public_key, name, value, timestamp, expires,
                  created_with, meta, signature, duplicate):
        """
        Will replicate args to "duplicate" number of nodes in the distributed
        hash table. Returns a deferred that will fire with a list of send_store
        deferreds when "duplicate" number of closest nodes have been
        identified.

        Obviously, the list can be turned in to a deferred_list to fire when
        the store commands have completed.

        Even if "duplicate" is > K no more than K items will be contained
        within the list result.
        """
        if duplicate < 1:
            # Guard to ensure meaningful duplication count.
            raise ValueError('Duplication count may not be less than 1')

        result = defer.Deferred()
        compound_key = construct_key(public_key, name)
        lookup = NodeLookup(compound_key, FindNode, self)

        def on_success(nodes):
            """
            A list of close nodes have been found so send store messages to
            the "duplicate" closest number of them and fire the "result"
            deferred with the resulting DeferredList of pending deferreds.
            """
            deferreds = self._process_lookup_result(nodes, public_key, name,
                                                    value, timestamp, expires,
                                                    created_with, meta,
                                                    signature, duplicate)
            result.callback(deferreds)

        def on_error(error):
            """
            Catch all for errors during the lookup phase. Simply pass them on
            via the "result" deferred.
            """
            result.errback(error)

        lookup.addCallback(on_success)
        lookup.addErrback(on_error)
        return result

    def retrieve(self, key):
        """
        Given a key, will try to retrieve associated value from the distributed
        hash table. Returns a deferred that will fire when the operation is
        complete or failed.

        As the original Kademlia explains:

        "For caching purposes, once a lookup succeeds, the requesting node
        stores the <key, value> pair at the closest node it observed to the
        key that did not return the value."

        This method adds a callback to the NodeLookup to achieve this end.
        """
        lookup = NodeLookup(key, FindValue, self)

        def cache(result):
            """
            Called once the lookup succeeds in order to store the item at the
            node closest to the key that did not return the value.
            """
            caching_contact = None
            for candidate in lookup.shortlist:
                if candidate in lookup.contacted:
                    caching_contact = candidate
                    break
            if caching_contact:
                log.msg("Caching to %r" % caching_contact)
                self.send_store(caching_contact, result.public_key,
                                result.name, result.value, result.timestamp,
                                result.expires, result.created_with,
                                result.meta, result.sig)
            return result

        lookup.addCallback(cache)
        return lookup

    def republish(self, message):
        """
        Will check and republish a locally stored message to the wider network.

        From the original Kademlia paper:

        "To ensure the persistence of key-value pairs, nodes must periodically
        republish keys. Otherwise, two phenomena may cause lookups for valid
        keys to fail. First, some of the k nodes that initially get a key-value
        pair when it is published may leave the network. Second, new nodes may
        join the network with IDs closer to some published key than the nodes
        on which the key-value pair was originally published. In both cases,
        the nodes with a key-value pair must republish it so as once again to
        ensure it is available on the k nodes closest to the key.

        To compensate for nodes leaving the network, Kademlia republishes each
        key-value pair once an hour. A naive implementation of this strategy
        would require many messages - each of up to k nodes storing a key-value
        pair would perform a node lookup followed by k - 1 STORE RPCs every
        hour. Fortunately, the republish process can be heavily optimized.
        First, when a node receives a STORE RPC for a given key-value pair, it
        assumes the RPC was also issued to the other k - 1 closest nodes, and
        thus the recipient will not republish the key-value pair in the next
        hour. This ensures that as long as republication intervals are not
        exactly synchronized, only one node will republish a given key-value
        pair every hour.

        A second optimization avoids performing node lookups before
        republishing keys. As described in Section 2.4, to handle unbalanced
        trees, nodes split k-buckets as required to ensure they have complete
        knowledge of a surrounding subtree with at least k nodes. If, before
        republishing key-value pairs, a node u refreshes all k-buckets in this
        subtree of k nodes, it will automatically be able to figure out the
        k closest nodes to a given key. These bucket refreshes can be amortized
        over the republication of many keys.

        To see why a node lookup is unnecessary after u refreshes buckets in
        the sub-tree of size >= k, it is necessary to consider two cases. If
        the key being republished falls in the ID range of the subtree, then
        since the subtree is of size at least k and u has complete knowledge of
        the subtree, clearly u must know the k closest nodes to the key. If,
        on the other hand, the key lies outside the subtree, yet u was one of
        the k closest nodes to the key, it must follow that u's k-buckets for
        intervals closer to the key than the subtree all have fewer than k
        entries. Hence, u will know all nodes in these k-buckets, which
        together with knowledge of the subtree will include the k closest nodes
        to the key.

        When a new node joins the system, it must store any key-value pair to
        which is is one of the k closest. Existing nodes, by similarly
        exploiting complete knowledge of their surrounding subtrees, will know
        which key-value pairs the new node should store. Any node learning of a
        new node therefore issues STORE RPCs to transfer relevant key-value
        pairs to the new node. To avoid redundant STORE RPCs, however, a node
        only transfers a key-value pair if it's [sic] own ID is closer to the
        key than are the IDs of other nodes."

        Messages are only republished if the following requirements are met:

        * They still exist in the local data store.
        * They have not expired.
        * They have not been updated for REPLICATE_INTERVAL seconds.
        """
        pass
