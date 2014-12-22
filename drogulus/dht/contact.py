# -*- coding: utf-8 -*-
"""
Defines a peer node on the network.
"""
from hashlib import sha512


def make_network_id(public_key):
    """
    Given a public_key as a string will return a canonical network_id.

    The network id is created as the hexdigest of the SHA512 of the public
    key.

    Will raise a ValueError if the incoming public_key is empty.
    """
    if public_key:
        return sha512(public_key.encode('ascii')).hexdigest()
    else:
        raise ValueError('Cannot create network_id from empty public key.')


class PeerNode(object):
    """
    Represents another node on the network.
    """

    def __init__(self, public_key, version, uri, last_seen=0.0):
        """
        Initialise the peer node with a unique id within the network (derived
        from its public key), the drogulus version the contact is running, a
        URI that identifies where to contact the peer node and a timestamp
        indicating when the last connection was made with the contact
        (defaults to 0).
        """
        self.network_id = make_network_id(public_key)
        self.public_key = public_key
        self.version = version
        self.uri = uri
        self.last_seen = last_seen
        # failed_RPCs keeps track of the number of failed RPCs to this peer.
        # If this number reaches a threshold then it is evicted from a
        # bucket and replaced with another node that is more reliable.
        self.failed_RPCs = 0

    def dump(self):
        """
        Returns a dictionary representation of the peer node that can be
        serialised into JSON. Useful for backing up the routing table.
        """
        return {
            'public_key': self.public_key,
            'version': self.version,
            'uri': self.uri,
        }

    def __eq__(self, other):
        """
        Override equals to work with a string representation of the contact's
        id.
        """
        if isinstance(other, PeerNode):
            return self.network_id == other.network_id
        elif isinstance(other, str):
            return self.network_id == other
        else:
            return False

    def __ne__(self, other):
        """
        Override != to work with a string representation of the contact's id.
        """
        return not self == other

    def __repr__(self):
        """
        Returns a tuple containing information about this contact.
        """
        return str((self.network_id, self.public_key, self.version, self.uri,
                    self.last_seen, self.failed_RPCs))

    def __str__(self):
        """
        Override the string representation of the object to be something
        useful.
        """
        return str({
            'network_id': self.network_id,
            'public_key': self.public_key,
            'version': self.version,
            'uri': self.uri,
            'last_seen': self.last_seen,
            'failed_rpc': self.failed_RPCs
        })

    def __hash__(self):
        """
        Create a Python hash so instances of this class can be used as keys in
        Python dics and members of Python sets.
        """
        return hash(self.network_id)
