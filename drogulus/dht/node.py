# -*- coding: utf-8 -*-
"""
Contains code that defines the behaviour of the local node in the DHT network.
"""
from .routingtable import RoutingTable
from .lookup import Lookup
from .storage import DictDataStore
from .contact import PeerNode
from .crypto import check_seal, get_seal, verify_item, construct_key
from .errors import (BadMessage, ExpiredMessage, OutOfDateMessage,
                     UnverifiableProvenance, TimedOut)
from .messages import (OK, Store, FindNode, Nodes, FindValue,
                       Value, from_dict, to_dict)
from .constants import (REPLICATE_INTERVAL, REFRESH_INTERVAL,
                        RESPONSE_TIMEOUT, K)
from ..version import get_version
import logging
import time
import asyncio
from hashlib import sha512
from uuid import uuid4


log = logging.getLogger(__name__)


class Node(object):
    """
    This class represents a single local node in the DHT encapsulating its
    presence in the network.

    All interactions with the DHT network are performed via this class (or a
    subclass).
    """

    def __init__(self, public_key, private_key, event_loop, connector,
                 reply_port):
        """
        Initialises the node with the credentials, event loop and object
        via which the node opens connections to peers. The reply_port
        argument tells other nodes on the network the port to use to contact
        this node. Such a port may not be the port used by the local machine
        but could be, for example, the port assigned by the UPnP setup of the
        local router.
        """
        self.public_key = public_key
        self.private_key = private_key
        self.event_loop = event_loop
        self.connector = connector
        self.reply_port = reply_port
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
        log.info('Initialised node with id: {}'.format(self.network_id))

    def join(self, data_dump):
        """
        Causes the Node to join the DHT network. This should be called before
        any other DHT operations. The seed_nodes argument must be a list of
        already known contacts describing existing nodes on the network.
        """
        if not data_dump.get('contacts', []):
            raise ValueError('Cannot join network: no contacts supplied')
        self.routing_table.restore(data_dump)
        # Ensure the refresh of k-buckets is set up properly.
        self.event_loop.call_later(REFRESH_INTERVAL, self.refresh)
        # Looking up the node's ID on the network will populate the routing
        # table with fresh nodes as well as tell us who our nearest neighbours
        # are.
        return Lookup(FindNode, self.network_id, self, self.event_loop)

    def message_received(self, message, protocol, address, port):
        """
        Handles incoming messages.

        The protocol, address and port arguments are used to create the
        remote contact's URI used to identify them on the network.
        """
        # Check the "seal" of the sender to make sure it's legit.
        if not check_seal(message):
            raise BadMessage()
        # Update the routing table.
        uri = '{protocol}://{address}:{port}'.format(protocol=protocol,
                                                     address=address,
                                                     port=port)
        other_node = PeerNode(message.sender, message.version, uri,
                              time.time())
        log.info('Message received from {}'.format(other_node))
        log.info(message)
        self.routing_table.add_contact(other_node)
        # Sort on message type and pass to handler method. Explicit > implicit.
        try:
            if isinstance(message, OK):
                return self.handle_ok(message)
            elif isinstance(message, Store):
                return self.handle_store(message, other_node)
            elif isinstance(message, FindNode):
                return self.handle_find_node(message, other_node)
            elif isinstance(message, FindValue):
                return self.handle_find_value(message, other_node)
            elif isinstance(message, Value):
                return self.handle_value(message, other_node)
            elif isinstance(message, Nodes):
                return self.handle_nodes(message)
        except Exception as ex:
            log.error('Problem handling message from {}'.format(other_node))
            log.error(message)
            log.error(ex)

    def send_message(self, contact, message, fire_and_forget=False):
        """
        Sends a message to the specified contact, adds the resulting future to
        the pending dictionary and ensures it times-out after the correct
        period. A callback is added to ensure that the task is removed from
        pending when it resolves (no matter the result). A timeout function
        is scheduled after RESPONSE_TIMEOUT seconds to clean up the pending
        task if the remote peer doesn't respond in a timely fashion.
        """
        # A Future that represents the delivery of the message.
        delivery = self.connector.send(contact, message, self)
        # A Future that resolves with the response to the outgoing message.
        response_received = asyncio.Future()
        self.pending[message.uuid] = response_received

        def on_delivery(task, node=self, response_received=response_received,
                        message=message):
            """
            Called when the delivery of the message either succeeds or fails.
            If the delivery failed then punish the remote peer and resolve
            response_received appropriately. Otherwise make sure the
            appropriate timeout or fire-and-forget handling is put in place
            on the response_received Future.
            """
            if task.exception():
                node.routing_table.remove_contact(contact.network_id)
                if not response_received.done():
                    response_received.set_exception(task.exception())
            else:
                if fire_and_forget:
                    node.event_loop.call_soon(response_received.set_result,
                                              'sent')
                else:
                    error = TimedOut('Response took too long.')
                    node.event_loop.call_later(RESPONSE_TIMEOUT,
                                               node.trigger_task,
                                               message, error)

        delivery.add_done_callback(on_delivery)

        def on_response(future, uuid=message.uuid):
            """
            Ensure the resolved response_received is removed from the pending
            dictionary.
            """
            if uuid in self.pending:
                del self.pending[uuid]

        response_received.add_done_callback(on_response)
        return message.uuid, response_received

    def trigger_task(self, message, error=False):
        """
        Given a message, will attempt to retrieve the related pending task
        and trigger it with the message.
        """
        if message.uuid in self.pending:
            task = self.pending[message.uuid]
            if not task.done():
                if error:
                    task.set_exception(error)
                else:
                    task.set_result(message)
            # Remove the resolved task from the pending dictionary.
            del self.pending[message.uuid]

    def handle_ok(self, message):
        """
        Handles an incoming ok message.
        """
        self.trigger_task(message)

    def handle_store(self, message, contact):
        """
        Handles an incoming Store message. Checks the provenance and timeliness
        of the message before storing locally. If there is a problem, removes
        the untrustworthy peer from the routing table. Otherwise, at
        REPLICATE_INTERVAL minutes in the future, the local node will attempt
        to replicate the Store message elsewhere in the DHT if such time is
        <= the message's expiry time.

        Sends an OK message if successful.
        """
        # Check provenance
        if verify_item(to_dict(message)):
            # Ensure the key is correct.
            k = construct_key(message.public_key, message.name)
            if k != message.key:
                # This may indicate a different / unknown / unsupported
                # version of the drogulus created the original message.
                raise BadMessage('Key mismatch')
            # Ensure the value isn't expired.
            now = time.time()
            if message.expires > 0 and (message.expires < now):
                # There's a non-zero expiry and it's less than the current
                # time, so return an error.
                raise ExpiredMessage(
                    'Expired at {} (current time: {})'.format(message.expires,
                                                              now))
            # Ensure the node doesn't already have a more up-to-date version
            # of the value.
            current = self.data_store.get(message.key, False)
            if current and (message.timestamp < current.timestamp):
                # The node already has a later version of the value so
                # return an error.
                raise OutOfDateMessage(
                    'Most recent timestamp: {}'.format(current.timestamp))
            # Good to go, so store value.
            self.data_store[message.key] = message
            # At some future time attempt to replicate the Store message
            # around the network IF it is within the message's expiry time.
            self.event_loop.call_later(REPLICATE_INTERVAL, self.republish,
                                       message.key)
            # Reply with an OK so the other end updates its routing table.
            return self.make_ok(message)
        else:
            # Remove from the routing table.
            log.error('Problem with Store command from {}'.format(contact))
            self.routing_table.blacklist(contact)
            raise UnverifiableProvenance('Blacklisted')

    def handle_find_node(self, message, contact):
        """
        Handles an incoming FindNode message. Finds the details of up to K
        other nodes closer to the target key that *this* node knows about.
        Responds with a "Nodes" message containing the list of matching
        nodes.
        """
        target_key = message.key
        # List containing tuples of information about the matching contacts.
        other_nodes = [[n.public_key, n.version, n.uri] for n in
                       self.routing_table.find_close_nodes(target_key)]
        return self.make_nodes(message, other_nodes)

    def handle_find_value(self, message, contact):
        """
        Handles an incoming FindValue message. If the local node contains the
        value associated with the requested key replies with an appropriate
        "Value" message. Otherwise, responds with details of up to K other
        nodes closer to the target key that the local node knows about. In
        this case a "Nodes" message containing the list of matching nodes is
        sent to the remote peer.
        """
        match = self.data_store.get(message.key, False)
        if match:
            # Update the last access time for the matching value.
            self.data_store.touch(message.key)
            return self.make_value(message, match.key, match.value,
                                   match.timestamp, match.expires,
                                   match.created_with, match.public_key,
                                   match.name, match.signature)
        else:
            return self.handle_find_node(message, contact)

    def handle_value(self, message, contact):
        """
        Handles an incoming Value message containing a value retrieved from
        another node on the DHT. Ensures the message is valid and resolves the
        referenced future to signal the arrival of the value.

        If the value is invalid then the reponse is logged, the remote peer
        is blacklisted and the referenced future is resolved with an
        UnverifiableProvenance exception.
        """
        if verify_item(to_dict(message)):
            self.trigger_task(message)
        else:
            log.error(
                'Problem with incoming Value message from {}'.format(contact))
            log.error(message)
            self.routing_table.remove_contact(contact.network_id, True)
            log.error('Remote peer removed from routing table.')
            self.trigger_task(message,
                              error=UnverifiableProvenance('Blacklisted'))

    def handle_nodes(self, message):
        """
        Handles an incoming Nodes message containing information about other
        nodes on the network that are close to a requested key.
        """
        self.trigger_task(message)

    def make_ok(self, message):
        """
        Returns an OK acknowledgement appropriate given the incoming message.
        """
        ok = {
            'uuid': message.uuid,
            'recipient': message.sender,
            'sender': self.public_key,
            'reply_port': self.reply_port,
            'version': self.version
        }
        seal = get_seal(ok, self.private_key)
        ok['seal'] = seal
        ok['message'] = 'ok'
        return from_dict(ok)

    def make_value(self, message, key, value, timestamp, expires,
                   created_with, public_key, name, signature):
        """
        Returns a valid Value message in response to the referenced message.
        """
        msg_dict = {
            'uuid': message.uuid,
            'recipient': message.sender,
            'sender': self.public_key,
            'reply_port': self.reply_port,
            'version': self.version,
            'key': key,
            'value': value,
            'timestamp': timestamp,
            'expires': expires,
            'created_with': created_with,
            'public_key': public_key,
            'name': name,
            'signature': signature,
        }
        seal = get_seal(msg_dict, self.private_key)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'value'
        return from_dict(msg_dict)

    def make_nodes(self, message, nodes):
        """
        Returns a valid Nodes message in response to the referenced incoming
        message.
        """
        msg_dict = {
            'uuid': message.uuid,
            'recipient': message.sender,
            'sender': self.public_key,
            'reply_port': self.reply_port,
            'version': self.version,
            'nodes': nodes,
        }
        seal = get_seal(msg_dict, self.private_key)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'nodes'
        return from_dict(msg_dict)

    def send_store(self, contact, key, value, timestamp, expires,
                   created_with, public_key, name, signature):
        """
        Sends a Store message to the given contact. The value contained within
        the message is stored against a key derived from the public_key and
        name. Furthermore, the message is cryptographically signed using the
        value, timestamp, expires, name and meta values.
        """
        msg_dict = {
            'uuid': str(uuid4()),
            'recipient': contact.public_key,
            'sender': self.public_key,
            'reply_port': self.reply_port,
            'version': self.version,
            'key': key,
            'value': value,
            'timestamp': timestamp,
            'expires': expires,
            'created_with': created_with,
            'public_key': public_key,
            'name': name,
            'signature': signature,
        }
        seal = get_seal(msg_dict, self.private_key)
        msg_dict['seal'] = seal
        msg_dict['message'] = 'store'
        message = from_dict(msg_dict)
        return self.send_message(contact, message)

    def send_find(self, contact, target, message_type):
        """
        Sends a Find[Node|Value] message to the given contact with the
        intention of obtaining information at the given target key. The type of
        find message is specified by message_type.

        This method is called by an instance of the Lookup class.
        """
        msg_dict = {
            'uuid': str(uuid4()),
            'recipient': contact.public_key,
            'sender': self.public_key,
            'reply_port': self.reply_port,
            'version': self.version,
            'key': target,
        }
        seal = get_seal(msg_dict, self.private_key)
        msg_dict['seal'] = seal
        if message_type is FindNode:
            msg_dict['message'] = 'findnode'
        else:
            msg_dict['message'] = 'findvalue'
        message = from_dict(msg_dict)
        return self.send_message(contact, message)

    def _store_to_nodes(self, nearest_nodes, duplicate, key, value, timestamp,
                        expires, created_with, public_key, name, signature):
        """
        Given a list of nearest nodes will return a list of send_store based
        tasks for the item based upon the args to be stored in the DHT at
        those locations. The list will contain up to "duplicate" number of
        pending tasks.
        """
        # Guards to ensure meaningful duplication.
        if duplicate < 1:
            raise ValueError('Duplication count may not be less than 1')
        if len(nearest_nodes) < 1:
            raise ValueError('Empty list of nearest nodes.')

        list_of_tasks = []
        for contact in nearest_nodes[:duplicate]:
            uuid, task = self.send_store(contact, key, value, timestamp,
                                         expires, created_with, public_key,
                                         name, signature)
            list_of_tasks.append(task)
        return list_of_tasks

    def replicate(self, duplicate, key, value, timestamp, expires,
                  created_with, public_key, name, signature):
        """
        Will replicate item to "duplicate" number of nodes in the distributed
        hash table. Returns a task that will fire with a list of send_store
        tasks when "duplicate" number of closest nodes have been identified.

        Obviously, the list can be consumed by asycnio.wait or asyncio.gather
        to fire when the store commands have completed.
        """
        if duplicate < 1:
            # Guard to ensure meaningful duplication count. This may save
            # time.
            raise ValueError('Duplication count may not be less than 1')

        result = asyncio.Future()
        compound_key = construct_key(public_key, name)
        lookup = Lookup(FindNode, compound_key, self, self.event_loop)
        if lookup.done():
            # If we get here it's because lookup couldn't start due to an
            # empty routing table.
            result.set_exception(lookup.exception())
            return result

        def on_result(r, duplicate=duplicate, result=result, key=key,
                      value=value, timestamp=timestamp, expires=expires,
                      created_with=created_with, public_key=public_key,
                      name=name, signature=signature):
            """
            To be called when the lookup completes.

            If successful, send a store message to "duplicate" number of
            contacts in the list of the close nodes have been found have by
            the lookup and resolve the "result" Future with the resulting
            list of pending tasks.

            If there was an error simply pass the exception on via the
            Future representing the result.
            """
            try:
                contacts = r.result()
                tasks = self._store_to_nodes(contacts, duplicate, key, value,
                                             timestamp, expires, created_with,
                                             public_key, name, signature)
                result.set_result(tasks)
            except Exception as ex:
                result.set_exception(ex)

        lookup.add_done_callback(on_result)
        return result

    def retrieve(self, key):
        """
        Given a key, will try to retrieve associated value from the distributed
        hash table. Returns a Future that will resolve when the operation is
        complete or failed.

        As the original Kademlia explains:

        "For caching purposes, once a lookup succeeds, the requesting node
        stores the <key, value> pair at the closest node it observed to the
        key that did not return the value."

        This method adds a callback to the NodeLookup to achieve this end.
        """
        lookup = Lookup(FindValue, key, self, self.event_loop)
        if lookup.done():
            # If we get here it's because lookup couldn't start due to an
            # empty routing table.
            return lookup

        def cache_result(lookup):
            """
            Called once the lookup resolves in order to store the item at the
            node closest to the key that did not return the value. If the
            lookup encountered an exception then no further action is taken.
            """
            if lookup.exception():
                return
            caching_contact = None
            for candidate in lookup.shortlist:
                if candidate in lookup.contacted:
                    caching_contact = candidate
                    break
            if caching_contact:
                log.info("Caching to {}".format(caching_contact))
                result = lookup.result()
                self.send_store(caching_contact, lookup.target, result.value,
                                result.timestamp, result.expires,
                                result.created_with, result.public_key,
                                result.name, result.signature)

        lookup.add_done_callback(cache_result)
        return lookup

    def refresh(self):
        """
        A periodically called method that will check and refresh the k-buckets
        in the node's routing table.
        """
        refresh_ids = self.routing_table.get_refresh_list()
        log.info('Refreshing buckets with ids: {}'.format(refresh_ids))
        for network_id in refresh_ids:
            Lookup(FindNode, network_id, self, self.event_loop)
        # schedule the next refresh.
        self.event_loop.call_later(REFRESH_INTERVAL, self.refresh)

    def republish(self, item_key):
        """
        Periodically called to check and republish a locally stored item to
        the wider network.

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
        pair every hour."

        In this implementation, messages are only republished if the following
        requirements are met:

        * The item still exists in the local data store (it may have been
        deleted in the time between the time of the call and the time the call
        was scheduled).
        * The item has not expired.
        * The item has not been updated for REPLICATE_INTERVAL seconds.

        Furthermore, the item is deleted from the local data store (after
        republication) if the item has not been requested during the proceeding
        REPLICATE_INTERVAL seconds. This ensures items are not over-cached but
        remain stored at peer nodes whose network ids are closest to the
        item's key.
        """
        log.info('Republish check for key: {}'.format(item_key))
        if item_key in self.data_store:
            item = self.data_store[item_key]
            now = time.time()
            if item.expires > 0.0 and item.expires < now:
                # The item has expired. If the item's expiry is 0 (or less)
                # then the item should never expire.
                del self.data_store[item_key]
                log.info('{} expired. Deleted from local data store.'
                         .format(item_key))
            else:
                updated = self.data_store.updated(item_key)
                accessed = self.data_store.accessed(item_key)
                update_delta = now - updated
                access_delta = now - accessed
                replicated = False
                if update_delta > REPLICATE_INTERVAL:
                    # The item needs republishing because it hasn't been
                    # updated within the specified time interval.
                    log.info('Republishing item {}.'.format(item_key))
                    self.replicate(K, item.key, item.value, item.timestamp,
                                   item.expires, item.created_with,
                                   item.public_key, item.name, item.signature)
                    replicated = True
                # Re-schedule the republication check.
                handler = self.event_loop.call_later(REPLICATE_INTERVAL,
                                                     self.republish, item_key)
                if access_delta > REPLICATE_INTERVAL:
                    # The item has not been accessed for a while so, if
                    # required, replicate the item and then remove it from the
                    # local data store. Remember to cancel the scheduled
                    # republication check.
                    log.info('Removing {} due to lack of activity.'
                             .format(item_key))
                    if not replicated:
                        self.replicate(K, item.key, item.value,
                                       item.timestamp, item.expires,
                                       item.created_with, item.public_key,
                                       item.name, item.signature)
                    del self.data_store[item_key]
                    handler.cancel()
        else:
            log.info('{} is no longer in local data store. Cancelled.'
                     .format(item_key))
