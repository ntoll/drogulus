# -*- coding: utf-8 -*-
"""
Ensures the DHT implementation has the required constants defined
"""
from drogulus import constants
import unittest


class TestConstants(unittest.TestCase):
    """
    Ensures the drogulus.dht.constants module contains the required / expected
    declarations.
    """

    def test_ALPHA(self):
        """
        The alpha number represents the degree of parallelism in network calls.
        """
        self.assertIsInstance(constants.ALPHA, int,
                              "constants.ALPHA must be an integer.")

    def test_K(self):
        """
        The k number (so named from the original Kademlia paper) defines the
        maximum number of contacts stored in a k-bucket. This should be an even
        number.
        """
        self.assertIsInstance(constants.K, int,
                              "constants.K must be an integer.")
        self.assertEqual(0, constants.K % 2)

    def test_RPC_TIMEOUT(self):
        """
        The rpc timeout number defines the timeout for network operations in
        seconds.
        """
        self.assertIsInstance(constants.RPC_TIMEOUT, int,
                              "constants.RPC_TIMEOUT must be an integer.")

    def test_ITERATIVE_LOOKUP_DELAY(self):
        """
        The iterative lookup delay defines the delay (in seconds) between
        iterations of iterative node lookups for loose parallelism.
        """
        self.assertIsInstance(constants.ITERATIVE_LOOKUP_DELAY, int,
                              "constants.ITERATIVE_LOOKUP_DELAY must be an " +
                              "integer.")

    def test_REFRESH_TIMEOUT(self):
        """
        The refresh timeout defines how long to wait (in seconds) before an
        unused k-bucket is refreshed.
        """
        self.assertIsInstance(constants.REFRESH_TIMEOUT, int,
                              "constants.REFRESH_TIMEOUT must be an integer.")

    def test_REPLICATE_INTERVAL(self):
        """
        The replication interval defines how long to wait (in seconds) before a
        node replicates (republishes / refreshes) any data it stores.
        """
        self.assertIsInstance(constants.REPLICATE_INTERVAL, int,
                              "constants.REPLICATE_INTERVAL must be an " +
                              "integer.")

    def test_REFRESH_INTERVAL(self):
        """
        The refresh interval defines how long to wait (in seconds) before a
        node checks whether any buckets need refreshing or data needs
        republishing.
        """
        self.assertIsInstance(constants.REFRESH_INTERVAL, int,
                              "constants.REFRESH_INTERVAL must be an integer.")

    def test_ERRORS(self):
        """
        The ERRORS dictionary defines the error codes (keys) and associated
        messages (values) that are used in error messages sent between nodes in
        the DHT.
        """
        self.assertIsInstance(constants.ERRORS, dict,
                              "constants.ERRORS must be a dictionary.")
