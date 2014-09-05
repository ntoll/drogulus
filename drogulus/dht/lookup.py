# -*- coding: utf-8 -*-
"""
Contains code that defines the behaviour of the local node in the DHT network.
"""
import asyncio
import time
import logging
from . import constants
from .contact import PeerNode
from .utils import sort_peer_nodes
from .errors import RoutingTableEmpty, ValueNotFound
from .messages import Nodes, FindValue, Value


log = logging.getLogger(__name__)


class Lookup(asyncio.Future):
    """
    Encapsulates a lookup in the DHT given a particular target key and message
    type. Will callback when a result is found or errback otherwise. If
    defined, will timeout.

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

    self.target - the lookup target expressed as a hexdigest of a sha512.
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
       cancel any pending requests and error with an OutOfTime error. The
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
       self.pending_requests and fire a callback with the returned value.
       If the value is invalid remove the node from self.shortlist and start
       from step 3 again without cancelling the other pending calls.

    8. If a list of closer nodes is returned by a peer add them to
       self.shortlist and sort - making sure nodes in self.contacted are not
       mistakenly re-added to the shortlist.

    9. If the nearest node in the newly sorted self.shortlist is closer to the
       target than self.nearest_node then set self.nearest_node to the new
       closer node and start from step 3 again.

    10. If self.nearest_node remains unchanged DO NOT start a new call.

    11. If there are no other requests in self.pending_requests then check that
        the constants.K nearest nodes in the self.contacted set are all closer
        than the nearest node in self.shortlist. If they are, and it's a
        FindNode message call back with the constants.K nearest nodes in the
        self.contacted set. If the message is a FindValue, errback with a
        ValueNotFound error.

    12. If there are still nearer nodes in self.shortlist to some of those in
        the constants.K nearest nodes in the self.contacted set then start
        from step 3 again (forcing the local node to contact the close nodes
        that have yet to be contacted).

    Note on validating values: In the future there may be constraints added to
    the FindValue query (such as only accepting values created after time T).
    """

    def __init__(self, message_type, target, local_node, event_loop,
                 timeout=constants.LOOKUP_TIMEOUT):
        """
        Sets up the lookup to search for a certain target key using the
        specified message time and the DHT state found in the local_node.
        Will cancel after timeout seconds.
        """
        asyncio.Future.__init__(self)
        self.message_type = message_type
        self.target = target
        self.local_node = local_node
        self.event_loop = event_loop
        # A set of nodes that have been contacted for this lookup.
        self.contacted = set()
        # Holds currently pending requests.
        self.pending_requests = {}
        # Schedule cancelling the lookup after a "timeout" amount of time.
        self.event_loop.call_later(timeout, self.cancel)
        # To hold peers in the DHT that are known to the local node that are
        # possibly close to the target key. Closest nodes come first.
        self.shortlist = self.local_node.routing_table.\
            find_close_nodes(target)
        if self.target != self.local_node.network_id:
            # Update the last_accessed attribute of the affected bucket. This
            # attribute is used to track the "freshness" of buckets.
            self.local_node.routing_table.touch_bucket(target)
        if not self.shortlist:
            # The node knows of no other nodes within the DHT.
            self.set_exception(RoutingTableEmpty())
            return
        # Holds the currently closest node to the target.
        self.nearest_node = self.shortlist[0]
        # Start the lookup process
        self._lookup()

    def _cancel_pending_requests(self):
        """
        Causes the Tasks waiting on pending requests to be cancelled in
        a clean non-blocking fashion.
        """
        for task in self.pending_requests.values():
            self.event_loop.call_soon(task.cancel)
        self.pending_requests = {}

    def cancel(self):
        """
        Cancels this lookup in a clean fashion.
        """
        if self.done():
            return False
        log.info('Cancelling lookup for {}'.format(self.target))
        self._cancel_pending_requests()
        return asyncio.Future.cancel(self)

    def _handle_error(self, uuid, contact, error):
        """
        Handles error conditions.

        If a node doesn't reply or an error is encountered it is removed from
        self.shortlist and self.pending_requests. Start the _lookup again.
        """
        if contact in self.shortlist:
            self.shortlist.remove(contact)
        if uuid in self.pending_requests:
            self.pending_requests[uuid].cancel()
            del self.pending_requests[uuid]
        log.info('Problem during interaction with {}'.format(contact))
        log.info(error)
        self._lookup()

    def _blacklist(self, contact):
        """
        Removes a contact from the shortlist and routing table while adding it
        to the global blacklist of misbehaving peers.
        """
        if contact in self.shortlist:
            self.shortlist.remove(contact)
        self.local_node.routing_table.blacklist(contact)
        log.info('Blacklisting {}'.format(repr(contact)))

    def _handle_response(self, uuid, contact, response):
        """
        Callback to handle expected responses (unexpected responses result in
        the remote node being blacklisted and a TypeError being thrown).

        When a response to a request is returned successfully remove the
        request from self.pending_requests.

        If it's a FindValue message and a suitable value is returned (see note
        at the end of these comments) cancel all the other pending calls in
        self.pending_requests and fire a callback with with the returned value.
        If the value is invalid blacklist the node, remove it from
        self.shortlist and start from step 3 again without cancelling the other
        pending calls.

        If a list of closer nodes is returned by a peer add them to
        self.shortlist and sort - making sure nodes in self.contacted are not
        mistakenly re-added to the shortlist.

        If the nearest node in the newly sorted self.shortlist is closer to the
        target than self.nearest_node then set self.nearest_node to the new
        closer node and start from step 3 again.

        If self.nearest_node remains unchanged DO NOT start a new lookup call.

        If there are no other requests in self.pending_requests then check that
        the constants.K nearest nodes in the self.contacted set are all closer
        than the nearest node in self.shortlist. If they are, and it's a
        FindNode message call back with the constants.K nearest nodes found in
        the self.contacted set. If the message is a FindValue, errback with a
        ValueNotFound error.

        If there are still nearer nodes in self.shortlist to some of those in
        the constants.K nearest nodes in the self.contacted set then start
        from step 3 again (forcing the local node to contact the close nodes
        that have yet to be contacted).

        Note on validating values: In the future there may be constraints added
        to the FindValue query (such as only accepting values created after
        time T).
        """
        # Remove originating request from pending requests.
        del self.pending_requests[uuid]

        # Attempt to process the result or handle problem cases appropriately.
        try:
            result = response.result()
            # Ensure the response is of the expected type[s].
            if not ((isinstance(result, Value) and
                     self.message_type == FindValue) or
                    isinstance(result, Nodes)):
                # Blacklist the problem contact from the routing table (since
                # it doesn't behave).
                self._blacklist(contact)
                raise TypeError("Unexpected response type from {}"
                                .format(contact))

            # Is the response the expected Value we're looking for..?
            if isinstance(result, Value):
                # Check if it's a suitable value (the key matches)
                if result.key == self.target:
                    # Ensure the Value has not expired.
                    if result.expires > 0 and (result.expires < time.time()):
                        # Do not blacklist expired nodes but simply remove
                        # them from the shortlist (handled by the
                        # _handle_error method).
                        raise ValueError("Expired value returned by {}"
                                         .format(contact))
                    # Cancel outstanding requests.
                    self._cancel_pending_requests()
                    # Ensure the returning contact is removed from the
                    # shortlist (so it's possible to discern the closest
                    # non-returning node)
                    if contact in self.shortlist:
                        self.shortlist.remove(contact)

                    # Success! The correct Value has been found. Set the
                    # result for this instance.
                    self.set_result(result)
                else:
                    # Blacklist the problem contact from the routing table
                    # since it's not behaving properly.
                    self._blacklist(contact)
                    raise ValueError("Value with wrong key returned by {}"
                                     .format(contact))
            else:
                # Otherwise it must be a Nodes message containing closer
                # nodes. Add the returned nodes to the shortlist. Sort the
                # shortlist in order of closeness to the target and ensure
                # the shortlist never gets longer than K.
                nodes = [PeerNode(n[0], n[1], n[2]) for n in result.nodes]
                candidate_contacts = [candidate for candidate in nodes
                                      if candidate not in self.shortlist]
                self.shortlist = sort_peer_nodes(candidate_contacts +
                                                 self.shortlist, self.target)
                # Check if the nearest_node remains unchanged.
                if self.nearest_node == self.shortlist[0]:
                    # Check for remaining pending requests.
                    if not self.pending_requests:
                        # Check all the candidates in the shortlist have been
                        # contacted.
                        candidates = [candidate for candidate
                                      in self.shortlist
                                      if candidate in self.contacted]
                        if len(candidates) == len(self.shortlist):
                            # There is a result.
                            if self.message_type == FindValue:
                                # Can't find a value at the key.
                                msg = "Unable to find value for key: {}"\
                                    .format(self.target)
                                self.set_exception(ValueNotFound(msg))
                            else:
                                # Success! Found nodes close to the specified
                                # target key.
                                self.set_result(self.shortlist)
                        else:
                            # There are still un-contacted peers in the
                            # shortlist so restart the lookup in order to
                            # check them.
                            self._lookup()
                    else:
                        # There are still pending requests to complete but do
                        # not restart the lookup
                        pass
                else:
                    # There is a new nearest node.
                    self.nearest_node = self.shortlist[0]
                    # Restart the lookup given the newly found nodes in the
                    # shortlist.
                    self._lookup()
        except Exception as ex:
            # Catch all for problems that ensures the error is correctly
            # handled, logged and the problem node is dealt with.
            self._handle_error(uuid, contact, ex)

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

                uuid, future = self.local_node.send_find(contact,
                                                         self.target,
                                                         self.message_type)
                self.pending_requests[uuid] = future
                self.contacted.add(contact)

                def callback(result, uuid=uuid, contact=contact):
                    """
                    Passes the result to the Lookup instance to handle.

                    The named arguments ensure the call to _handle_response
                    uses the values of uuid and contact that are in scope at
                    the time that this function is defined.

                    This is a bit of a hack. :-/
                    """
                    if not result.cancelled():
                        self._handle_response(uuid, contact, result)

                future.add_done_callback(callback)
