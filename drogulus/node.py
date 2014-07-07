# -*- coding: utf-8 -*-
"""
Contains the class that defines a node in the drogulus network.
"""
from .dht.node import Node
from .dht.constants import DUPLICATION_COUNT, EXPIRY_DURATION


class Drogulus:
    """
    Represents a node in the drogulus network.
    """

    def __init__(self, private_key, public_key, event_loop, alias=None):
        """
        The private and public keys are required for signing and verifying
        items and peers within the drogulus network. The event loop is an
        asyncio based event loop. The optional alias argument is a dict of
        alias -> public key mappings for friends in the network.
        """
        self.private_key = private_key
        self.public_key = public_key
        self.event_loop = event_loop
        self._node = Node()
        if alias:
            self.alias = alias
        else:
            self.alias = {}

    def join(self, peers):
        """
        Causes the node to join the distributed hash table by attempting to
        ping the passed in list of peer nodes. Returns a future that fires
        when the operation is complete.
        """
        # Fill the routing table.
        # Set your whois information.
        pass

    def whois(self, public_key):
        """
        Given the public key of an entity that uses the drogulus will return a
        future that fires when information about them stored in the DHT is
        retrieved.
        """
        return self.get(public_key, None)

    def get(self, public_key, key_name):
        """
        Gets the value associated with a compound key made of the passed in
        public key and meaningful key name. Returns a future that fires when
        the value is retrieved.
        """
        target = construct_key(public_key, key_name)
        return self._node.retrieve(target)

    def set(self, key_name, value, duplicate=DUPLICATION_COUNT,
            expires=EXPIRY_DURATION):
        """
        Stores a value at a compound key made from the local node's public key
        and the passed in meaningful key name. Returns a future that fires
        when the value has been stored to duplicate number of nodes. An
        expires duration (to be added to the current time) can also be
        specified.
        """
        timestamp = time.time()
        if expires < 1:
            expires = -1
        else:
            expires = timestamp + expires
        return self._node.replicate(key_name, value, timestamp, expires,
                                    duplicate)
