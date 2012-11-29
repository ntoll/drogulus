# -*- coding: utf-8 -*-
"""
Ensures details of contacts (other nodes on the network) are represented
correctly.
"""
from drogulus.dht.contact import Contact
from drogulus.version import get_version
import unittest


class TestContact(unittest.TestCase):
    """
    Ensures the Contact class works as expected.
    """

    def test_init(self):
        """
        Ensures an object is created as expected.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        self.assertEqual(id, contact.id)
        self.assertEqual(address, contact.address)
        self.assertEqual(port, contact.port)
        self.assertEqual(version, contact.version)
        self.assertEqual(last_seen, contact.last_seen)
        self.assertEqual(0, contact.failed_RPCs)

    def test_init_with_long_id(self):
        """
        If the ID is passed in as a long value ensure it's translated to the
        correct string representation of the hex version.
        """
        id = 12345L
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        expected = '09'
        self.assertEqual(expected, contact.id)
        self.assertEqual(12345L, long(contact.id.encode('hex'), 16))

    def test_init_with_int_id(self):
        """
        If the ID is passed in as an int value ensure it's translated to the
        correct string representation of the hex version.
        """
        id = 12345
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        expected = '09'
        self.assertEqual(expected, contact.id)
        self.assertEqual(12345L, long(contact.id.encode('hex'), 16))

    def test_eq(self):
        """
        Makes sure equality works between a string representation of an ID and
        a contact object.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        self.assertTrue(id == contact)

    def test_ne(self):
        """
        Makes sure non-equality works between a string representation of an ID
        and a contact object.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        self.assertTrue('54321' != contact)

    def test_str(self):
        """
        Ensures the string representation of a contact is something useful.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        version = get_version()
        last_seen = 123
        contact = Contact(id, address, port, version, last_seen)
        expected = "('12345', '192.168.0.1', 9999, '%s')" % version
        self.assertEqual(expected, str(contact))
