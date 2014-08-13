# -*- coding: utf-8 -*-
"""
Ensures details of contacts (peer nodes on the network) are represented
correctly.
"""
from hashlib import sha512
from drogulus.dht.contact import PeerNode
from drogulus.version import get_version
from .keys import PUBLIC_KEY
import unittest


class TestPeerNode(unittest.TestCase):
    """
    Ensures the PeerNode class works as expected.
    """

    def test_init(self):
        """
        Ensures an object is created as expected.
        """
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        hex_digest = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        self.assertEqual(contact.network_id, hex_digest)
        self.assertEqual(version, contact.version)
        self.assertEqual(uri, contact.uri)
        self.assertEqual(last_seen, contact.last_seen)
        self.assertEqual(0, contact.failed_RPCs)

    def test_eq(self):
        """
        Makes sure equality works between a string representation of an ID and
        a PeerNode object.
        """
        network_id = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        version = get_version()
        uri = 'netstring://192.168.0.1:9999'
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        self.assertTrue(network_id == contact)

    def test_eq_other_peer(self):
        """
        Ensure equality works between two PeerNode instances.
        """
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact1 = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        contact2 = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        self.assertTrue(contact1 == contact2)

    def test_eq_wrong_type(self):
        """
        Ensure equality returns false if comparing a PeerNode with some other
        type of object.
        """
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        self.assertFalse(12345 == contact)

    def test_ne(self):
        """
        Makes sure non-equality works between a string representation of an ID
        and a PeerNode object.
        """
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        self.assertTrue('54321' != contact)

    def test_repr(self):
        """
        Ensure the repr for the object is something useful.
        """
        network_id = sha512(PUBLIC_KEY.encode('ascii')).hexdigest()
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        expected = str((network_id, PUBLIC_KEY, version, uri, last_seen, 0))
        self.assertEqual(expected, repr(contact))

    def test_str(self):
        """
        Ensures the string representation of a PeerContact is something
        useful.
        """
        uri = 'netstring://192.168.0.1:9999'
        version = get_version()
        last_seen = 123
        contact = PeerNode(PUBLIC_KEY, version, uri, last_seen)
        expected = str({
            'network_id': contact.network_id,
            'public_key': contact.public_key,
            'version': contact.version,
            'uri': contact.uri,
            'last_seen': contact.last_seen,
            'failed_rpc': contact.failed_RPCs
        })
        self.assertEqual(expected, str(contact))

    def test_hash(self):
        """
        Ensure the hash for the object is correct.
        """
        uri = 'netstring://192.168.0.1:9999'
        contact = PeerNode(PUBLIC_KEY, get_version(), uri, 0)
        expected = hash(sha512(PUBLIC_KEY.encode('ascii')).hexdigest())
        self.assertEqual(expected, hash(contact))
