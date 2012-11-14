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

    def testInit(self):
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

    def testEq(self):
        """
        Makes sure equality works between a string representation of an ID and
        a contact object.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        last_seen = 123
        contact = Contact(id, address, port, last_seen)
        self.assertTrue(id == contact)

    def testNe(self):
        """
        Makes sure non-equality works between a string representation of an ID
        and a contact object.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        last_seen = 123
        contact = Contact(id, address, port, last_seen)
        self.assertTrue('54321' != contact)

    def testStr(self):
        """
        Ensures the string representation of a contact is something useful.
        """
        id = '12345'
        address = '192.168.0.1'
        port = 9999
        last_seen = 123
        contact = Contact(id, address, port, last_seen)
        expected = ("('12345', '192.168.0.1', 9999)")
        self.assertEqual(expected, str(contact))
