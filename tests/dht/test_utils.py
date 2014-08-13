# -*- coding: utf-8 -*-
"""
Ensures the generic functions used in various places within the dht work as
expected.
"""
from drogulus.dht.utils import distance, sort_peer_nodes
from drogulus.dht.contact import PeerNode
from drogulus.dht import constants
from drogulus.version import get_version
import unittest


class TestUtils(unittest.TestCase):
    """
    Ensures the generic utility functions work as expected.
    """

    def setUp(self):
        """
        Common vars.
        """
        self.version = get_version()

    def test_distance(self):
        """
        Sanity check to ensure the XOR'd values return the correct distance.
        """
        key1 = 'deadbeef'
        key2 = 'beefdead'
        expected = int(key1, 16) ^ int(key2, 16)
        actual = distance(key1, key2)
        self.assertEqual(expected, actual)

    def test_sort_peer_nodes(self):
        """
        Ensures that the sort_peer_nodes function returns the list ordered in
        such a way that the contacts closest to the target key are at the head
        of the list.
        """
        contacts = []
        for i in range(512):
            uri = 'netstring://192.168.0.%d:9999' % i
            contact = PeerNode(str(i), self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            contacts.append(contact)
        target_key = hex(2 ** 256)
        result = sort_peer_nodes(contacts, target_key)

        # Ensure results are in the correct order.
        def key(node):
            return distance(node.network_id, target_key)
        sorted_nodes = sorted(result, key=key)
        self.assertEqual(sorted_nodes, result)
        # Ensure the order is from lowest to highest in terms of distance
        distances = [distance(x.network_id, target_key) for x in result]
        self.assertEqual(sorted(distances), distances)

    def test_sort_peer_nodes_no_longer_than_k(self):
        """
        Ensure that no more than constants.K contacts are returned from the
        sort_peer_nodes function despite a longer list being passed in.
        """
        contacts = []
        for i in range(512):
            uri = 'netstring://192.168.0.%d:9999' % i
            contact = PeerNode(str(i), self.version, uri, 0)
            contact.network_id = hex(2 ** i)
            contacts.append(contact)
        target_key = hex(2 ** 256)
        result = sort_peer_nodes(contacts, target_key)
        self.assertEqual(constants.K, len(result))
