# -*- coding: utf-8 -*-
"""
A rather silly test but added all the same for completeness and to check the
initial test suite works as expected.
"""
from drogulus.version import VERSION, get_version
import unittest


class TestVersion(unittest.TestCase):
    """
    Ensures the drogulus.version module works as expected.
    """

    def test_VERSION(self):
        """
        Ensures the VERSION is expressed correctly.
        """
        self.assertEqual(tuple, type(VERSION))
        self.assertTrue(isinstance(VERSION[0], int),
                        "VERSION's MAJOR element must be an integer")
        self.assertTrue(isinstance(VERSION[1], int),
                        "VERSION's MINOR element must be an integer")
        self.assertTrue(isinstance(VERSION[2], int),
                        "VERSION's RELEASE element must be an integer")
        self.assertTrue(isinstance(VERSION[3], str),
                        "VERSION's STATUS element must be an string")
        self.assertTrue(VERSION[3] in ('alpha', 'beta', 'final'),
                        "VERSION's STATUS element must be either 'alpha', " +
                        "'beta' or 'final' (currently set to %s)" % VERSION[3])
        self.assertTrue(isinstance(VERSION[4], int),
                        "VERSION's VERSION element must be an integer")

    def test_get_version(self):
        """
        Ensures the get_version function returns a dot separated expression of
        the VERSION.
        """
        expected = '.'.join([str(i) for i in VERSION])
        actual = get_version()
        self.assertEqual(expected, actual)
