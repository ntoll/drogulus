# -*- coding: utf-8 -*-
"""
Ensures the generic functions used in various places within the DHT
implementation work as expected.
"""
from drogulus.utils import long_to_hex, hex_to_long, distance, sort_contacts
from drogulus.dht.contact import Contact
from drogulus.version import get_version
from drogulus import constants
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

    def test_long_to_hex(self):
        """
        Ensure a long number produces the correct result.
        """
        raw = 123456789L
        result = long_to_hex(raw)
        self.assertEqual(raw, long(result.encode('hex'), 16))

    def test_hex_to_long(self):
        """
        Ensure a valid hex value produces the correct result.
        """
        raw = 'abcdef0123456789'
        result = hex_to_long(raw)
        self.assertEqual(raw, long_to_hex(result))

    def test_distance(self):
        """
        Sanity check to ensure the XOR'd values return the correct distance.
        """
        key1 = 'abc'
        key2 = 'xyz'
        expected = 1645337L
        actual = distance(key1, key2)
        self.assertEqual(expected, actual)

    def test_sort_contacts(self):
        """
        Ensures that the sort_contacts function returns the list ordered in
        such a way that the contacts closest to the target key are at the head
        of the list.
        """
        contacts = []
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, 9999, self.version,
                              0)
            contacts.append(contact)
        target_key = long_to_hex(2 ** 256)
        result = sort_contacts(contacts, target_key)
        # Ensure results are in the correct order.
        def key(node):
            return distance(node.id, target_key)
        sorted_nodes = sorted(result, key=key)
        self.assertEqual(sorted_nodes, result)
        # Ensure the order is from lowest to highest in terms of distance
        distances = [distance(x.id, target_key) for x in result]
        self.assertEqual(sorted(distances), distances)

    def test_sort_contacts_no_longer_than_k(self):
        """
        Ensure that no more than constants.K contacts are returned from the
        sort_contacts function despite a longer list being passed in.
        """
        contacts = []
        for i in range(512):
            contact = Contact(2 ** i, "192.168.0.%d" % i, 9999, self.version,
                              0)
            contacts.append(contact)
        target_key = long_to_hex(2 ** 256)
        result = sort_contacts(contacts, target_key)
        self.assertEqual(constants.K, len(result))
