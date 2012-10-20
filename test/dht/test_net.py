"""
Ensures the low level networking functions of the DHT behave as expected.
"""
import drogulus.dht.constants as constants
from drogulus.dht.net import DHTFactory
from twisted.trial import unittest
from twisted.test import proto_helpers

class TestDHTProtocol(unittest.TestCase):
    """
    Ensures the DHTProtocol works as expected.
    """

    def setUp(self):
        """
        Following the pattern explained here:

        http://twistedmatrix.com/documents/current/core/howto/trial.html
        """
        factory = DHTFactory()
        self.protocol = factory.buildProtocol(('127.0.0.1', 0))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)

    def _testIn(self, msg, expected):
        """
        Utility function that simulates the arrival of message and checks that
        the response is expected.
        """
        self.protocol.dataReceived(msg)
        self.assertEqual(self.transport.value(), expected)

    def _testOut(self):
        """
        Utility function that simulates the sending of a message and checks
        that the outgoing stream is as expected.

        TODO: Finish this!
        """
        pass

    def test_foo(self):
        """
        Sanity test to check I've wired things up correctly.

        TODO: Delete this and replace with *proper* tests.
        """
        return self._testIn('1:a,', 'a')
