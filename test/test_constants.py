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

    def test_LOOKUP_TIMEOUT(self):
        """
        The lookup timeout defines the default maximum amount of time a node
        lookup is allowed to take.
        """
        self.assertIsInstance(constants.LOOKUP_TIMEOUT, int,
                              "constants.LOOKUP_TIMEOUT must be an integer.")

    def test_RPC_TIMEOUT(self):
        """
        The rpc timeout number defines the timeout for network operations in
        seconds.
        """
        self.assertIsInstance(constants.RPC_TIMEOUT, int,
                              "constants.RPC_TIMEOUT must be an integer.")

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

    def test_ALLOWED_RPC_FAILS(self):
        """
        The allowed number of rpc failures defines the number of failed
        communication attempts are allowed to a peer before it is removed from
        the routing table.
        """
        self.assertIsInstance(constants.ALLOWED_RPC_FAILS, int,
                              "constants.ALLOWED_RPC_FAILS must be an " +
                              "integer.")

    def test_DUPLICATION_COUNT(self):
        """
        The duplication count defines the number of nodes to attempt to use to
        initially store a value in the DHT.
        """
        self.assertIsInstance(constants.DUPLICATION_COUNT, int,
                              "constants.DUPLICATION_COUNT must be an " +
                              "integer.")

    def test_EXPIRY_DURATION(self):
        """
        The expiry duration is the number of seconds that added to a value's
        creation time in order to work out its expiry timestamp.
        """
        self.assertIsInstance(constants.EXPIRY_DURATION, int,
                              "constants.EXPIRY_DURATION must be an integer.")

    def test_ERRORS(self):
        """
        The ERRORS dictionary defines the error codes (keys) and associated
        messages (values) that are used in error messages sent between nodes in
        the DHT.
        """
        self.assertIsInstance(constants.ERRORS, dict,
                              "constants.ERRORS must be a dictionary.")
