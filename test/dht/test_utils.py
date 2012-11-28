"""
Ensures the generic functions used in various places within the DHT
implementation work as expected.
"""
from drogulus.dht.utils import long_to_hex, hex_to_long
import unittest


class TestUtils(unittest.TestCase):
    """
    Ensures the generic utility functions work as expected.
    """

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
