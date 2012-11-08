"""
Ensures the low level networking functions of the DHT behave as expected.
"""
from drogulus.version import get_version
from drogulus.dht.constants import ERRORS
from drogulus.dht.net import DHTFactory
from drogulus.dht.node import Node
from drogulus.dht.messages import Pong, to_msgpack, from_msgpack
from twisted.trial import unittest
from twisted.test import proto_helpers
from uuid import uuid4
import hashlib
import time
import re


class TestDHTProtocol(unittest.TestCase):
    """
    Ensures the DHTProtocol works as expected.
    """

    def setUp(self):
        """
        Following the pattern explained here:

        http://twistedmatrix.com/documents/current/core/howto/trial.html
        """
        hasher = hashlib.sha1()
        hasher.update(str(time.time()))
        self.node_id = hasher.hexdigest()
        self.node = Node(self.node_id)
        self.factory = DHTFactory(self.node)
        self.protocol = self.factory.buildProtocol(('127.0.0.1', 0))
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

    def _to_netstring(self, raw):
        """
        Converts a raw msgpacked value into a netstring.
        """
        return '%d:%s,' % (len(raw), raw)

    def _from_netstring(self, raw):
        """
        Strips netstring related length and trailing comma from raw string.
        """
        # extract length:content
        length, content = raw.split(':', 1)
        # remove trailing comma
        return content[:-1]

    def test_string_received_except_to_error(self):
        """
        Sanity test to check error handling works as expected.
        """
        # Send bad message
        self.protocol.dataReceived('1:a,')
        # Check we receive the expected error in return
        raw_response = self.transport.value()
        msgpack_response = self._from_netstring(raw_response)
        err = from_msgpack(msgpack_response)
        self.assertEqual(3, err.code)
        self.assertEqual(ERRORS[3], err.title)
        self.assertEqual({}, err.details)
        uuidMatch = ('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-' +
                     '[a-f0-9]{12}')
        self.assertTrue(re.match(uuidMatch, err.uuid))

    def test_send_message(self):
        """
        Ensure the message passed into the protocol is turned into a netstring
        version of a msgpacked message.
        """
        # Create a simple Ping message
        uuid = str(uuid4())
        version = get_version()
        msg = Pong(uuid, version)
        # Send it down the wire...
        self.protocol.sendMessage(msg)
        # Check it's as expected.
        expected = self._to_netstring(to_msgpack(msg))
        actual = self.transport.value()
        self.assertEqual(expected, actual)
