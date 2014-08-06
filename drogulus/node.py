# -*- coding: utf-8 -*-
"""
Contains the class that defines a node in the drogulus network.
"""
from .dht.node import Node
from .dht.constants import DUPLICATION_COUNT, EXPIRY_DURATION
from .dht.crypto import construct_key
from .version import get_version
import asyncio
import time


class Drogulus:
    """
    Represents a node in the drogulus network. All the actual heavy lifting
    is done within this class's _node attribute (an instance of
    drogulus.dht.node.Node).
    """

    def __init__(self, private_key, public_key, event_loop, connector,
                 port=1908, alias=None, whoami=None):
        """
        The private and public keys are required for signing and verifying
        items and peers within the drogulus network. The event loop is an
        asyncio based event loop. The connector argument must be an instance
        of a child class of the Connector class. The optional port argument
        indicates the port to which remote notes should connect. The optional
        alias argument is a dict of alias -> public key mappings for friends
        in the network. The optional whoami argument is a dictionary of
        arbitrary data about the local node.
        """
        self.private_key = private_key
        self.public_key = public_key
        self.event_loop = event_loop
        self.connector = connector
        self._node = Node(private_key, public_key, event_loop,
                          connector, port)
        if alias:
            self.alias = alias
        else:
            self.alias = {}
        if whoami:
            self.whoami = whoami
        else:
            self.whoami = {}
        self.whoami['public_key'] = self.public_key
        self.whoami['version'] = get_version()

    def join(self, peers):
        """
        Causes the node to join the distributed hash table by attempting to
        ping the passed in list of peer nodes. Returns a future that fires
        when the operation is complete. Attempts to populate whoami data about
        the local node to the wider network.
        """
        future = self._node.join(peers)

        def on_joined(result, whois=self.whoami, node=self):
            """
            Called when the node has joined the network. Sets the node's
            whoami dict within the wider network.
            """
            node.set(whois['public_key'], whois)

        future.add_done_callback(on_joined)
        return future

    def whois(self, public_key):
        """
        Given the public key of an entity that uses the drogulus will return a
        future that fires when information about them stored in the DHT is
        retrieved.
        """
        return self.get(public_key, public_key)

    def get(self, public_key, key_name):
        """
        Gets the value associated with a compound key made of the passed in
        public key and meaningful key name. Returns a future that resolves
        when the value is retrieved.
        """
        target = construct_key(public_key, key_name)
        return self._node.retrieve(target)

    def set(self, key_name, value, duplicate=DUPLICATION_COUNT,
            expires=EXPIRY_DURATION):
        """
        Stores a value at a compound key made from the local node's public key
        and the passed in meaningful key name. Returns a future that resolves
        when the value has been stored to duplicate number of nodes (see
        https://docs.python.org/3.4/library/asyncio-task.html#asyncio.gather
        for more information about how this is done).

        An optional "duplicate" argument specifies the number of remote peers
        to replicate to. This defaults to the DEPLICATION_COUNT setting.

        An optional expires duration (to be added to the current time) is used
        to indicate when the supplied value should be removed from the DHT.
        This defaults to the EXPIRY_DURATION setting.
        """
        timestamp = time.time()
        if expires < 1:
            expires = -1
        else:
            expires = timestamp + expires
        tasks = self._node.replicate(key_name, value, timestamp, expires,
                                     duplicate)
        return asyncio.gather(*tasks, return_exceptions=True)
