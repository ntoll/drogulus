# -*- coding: utf-8 -*-
"""
Contains Exception derived classes used by the drogulus to report various
broken states.
"""


class BucketFull(Exception):
    """
    Raised when a bucket in the routing table is full.
    """
    pass


class RoutingTableEmpty(Exception):
    """
    Fired when a lookup is attempted without any peers in the local node's
    routing table.
    """
    pass


class ValueNotFound(Exception):
    """
    Fired when a Lookup instance cannot find a value associated with a
    specified key.
    """
    pass


class BadMessage(Exception):
    """
    The incoming message simply didn't make any sense.
    """
    pass


class ExpiredMessage(Exception):
    """
    The value in the incoming message appears to be expired from the local
    node's point of view.
    """
    pass


class OutOfDateMessage(Exception):
    """
    The value of the incoming message is out of date - the local node holds
    a later version of the value.
    """
    pass


class UnknownMessageType(Exception):
    """
    The incoming message was parsed but not recognised.
    """
    pass


class InternalError(Exception):
    """
    The incoming message was parsed and recognised but the receiving node
    encountered a problem when dealing with it.
    """
    pass


class TooBig(Exception):
    """
    The incoming message was too big for the receiving node to handle.
    """
    pass


class UnsupportedProtocol(Exception):
    """
    The incoming message uses a version of the protocol unsupported by the
    receiving node.
    """
    pass


class UnverifiableProvenance(Exception):
    """
    The incoming message could not be cryptographically verified by the
    receiving node.
    """
    pass


class TimedOut(Exception):
    """
    The expected response to an outgoing message was not received in a timely
    fashion.
    """
    pass
