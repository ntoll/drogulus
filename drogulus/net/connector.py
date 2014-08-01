# -*- coding: utf-8 -*-
"""
Contains the base class from which all connectors should inherit.

A connector class handles network connectivity and the sending and receiving
of messages.
"""


class Connector:
    """
    The base class for all connectors. Such classes handle connectivity and
    the sending and receiving of messages over the network. They should only
    implement two methods: send and receive.
    """

    def __init__(self, event_loop):
        """
        Instantiates the class with a reference to the asyncio eventloop to
        use to create connections to remote peers.
        """
        self.event_loop = event_loop

    def send(self, contact, message):
        """
        Sends the message instance to the referenced contact.
        """
        raise NotImplementedError()

    def receive(self, message, sender, handler, protocol):
        """
        Receives a raw message from a sender. The details of what both the
        message and sender arguments represent will be different for each
        child class. The handler argument is always a reference to the
        local node in the DHT.
        """
        raise NotImplementedError()
