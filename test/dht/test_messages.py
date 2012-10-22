"""
A set of sanity checks to ensure that the messages are defined as expected.
"""
from drogulus.dht.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
    FindValue, Value, to_msgpack, from_msgpack, make_message)
from drogulus.dht.constants import ERRORS
from drogulus.dht.crypto import construct_key, generate_signature
import unittest
import hashlib
import msgpack
import time
from uuid import uuid4


# Useful throw-away constants for testing purposes.
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXgIBAAKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQLN2RbbDIMHILA1i6wByXkqEa
mnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjGb+oGVTKizfbMbGCKZ8fT64ZZ
gan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M6WixkMTbFM91fW0mUwIDAQAB
AoGBAJvBENvj5wH1W2dl0ShY9MLRpuxMjHogo3rfQr/G60AkavhaYfKn0MB4tPYh
MuCgtmF+ATqaWytbq9oUNVPnLUqqn5M9N86+Gb6z8ld+AcR2BD8oZ6tQaiEIGzmi
L9AWEZZnyluDSHMXDoVrvDLxPpKW0yPjvQfWN15QF+H79faJAkEA0hgdueFrZf3h
os59ukzNzQy4gjL5ea35azbQt2jTc+lDOu+yjUic2O7Os7oxnSArpujDiOkYgaih
Dny+/bIgLQJBAOhGKjhpafdpgpr/BjRlmUHXLaa+Zrp/S4RtkIEkE9XXkmQjvVZ3
EyN/h0IVNBv45lDK0Qztjic0L1GON62Z8H8CQAcRkqZ3ZCKpWRceNXK4NNBqVibj
SiuC4/psfLc/CqZCueVYvTwtrkFKP6Aiaprrwyw5dqK7nPx3zPtszQxCGv0CQQDK
51BGiz94VAE1qQYgi4g/zdshSD6xODYd7yBGz99L9M77D4V8nPRpFCRyA9fLf7ii
ZyoLYxHFCX80fUoCKvG9AkEAyX5iCi3aoLYd/CvOFYB2fcXzauKrhopS7/NruDk/
LluSlW3qpi1BGDHVTeWWj2sm30NAybTHjNOX7OxEZ1yVwg==
-----END RSA PRIVATE KEY-----"""


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQ
LN2RbbDIMHILA1i6wByXkqEamnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjG
b+oGVTKizfbMbGCKZ8fT64ZZgan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M
6WixkMTbFM91fW0mUwIDAQAB
-----END PUBLIC KEY-----"""


class TestMessages(unittest.TestCase):
    """
    Ensures the message classes are *defined* as expected and the relevant
    fields can be indexed.
    """

    def setUp(self):
        self.uuid = str(uuid4())

    def test_error(self):
        """
        Expected behaviour of an error message.
        """
        error = Error(self.uuid, 2, 'This is an error', {'foo': 'bar'}, '0.1')
        self.assertEqual(self.uuid, error.uuid)
        self.assertEqual(2, error.code)
        self.assertEqual('This is an error', error.title)
        self.assertEqual({'foo': 'bar'}, error.details)
        self.assertEqual('0.1', error.version)

    def test_ping(self):
        """
        Expected behaviour of a ping message.
        """
        ping = Ping(self.uuid, '0.1')
        self.assertEqual(self.uuid, ping.uuid)
        self.assertEqual('0.1', ping.version)

    def test_pong(self):
        """
        Expected behaviour of a pong message.
        """
        pong = Pong(self.uuid, '0.1')
        self.assertEqual(self.uuid, pong.uuid)
        self.assertEqual('0.1', pong.version)

    def test_store(self):
        """
        Expected behaviour of a store message.
        """
        store = Store(self.uuid, 'abc123', 'value', 1350544046.084875,
            'abcdefg', 'name', {'meta': 'value'}, 'sig', '0.1')
        self.assertEqual(self.uuid, store.uuid)
        self.assertEqual('abc123', store.key)
        self.assertEqual('value', store.value)
        self.assertEqual(1350544046.084875, store.timestamp)
        self.assertEqual('abcdefg', store.public_key)
        self.assertEqual('name', store.name)
        self.assertEqual({'meta': 'value'}, store.meta)
        self.assertEqual('sig', store.sig)
        self.assertEqual('0.1', store.version)

    def test_find_node(self):
        """
        Expected behaviour of a findnode message.
        """
        fn = FindNode(self.uuid, 'key', '0.1')
        self.assertEqual(self.uuid, fn.uuid)
        self.assertEqual('key', fn.key)
        self.assertEqual('0.1', fn.version)

    def test_nodes(self):
        """
        Expected behaviour of a nodes message.
        """
        nodes = Nodes(self.uuid, (('127.0.0.1', 1908)), '0.1')
        self.assertEqual(self.uuid, nodes.uuid)
        self.assertEqual((('127.0.0.1', 1908)), nodes.nodes)
        self.assertEqual('0.1', nodes.version)

    def test_find_value(self):
        """
        Expected behaviour of a findvalue message.
        """
        fv = FindValue(self.uuid, 'key', '0.1')
        self.assertEqual(self.uuid, fv.uuid)
        self.assertEqual('key', fv.key)
        self.assertEqual('0.1', fv.version)

    def test_value(self):
        """
        Expected behaviour of a value message.
        """
        val = Value(self.uuid, 'abc123', 'value', 1350544046.084875,
            'abcdefg', 'name', {'meta': 'value'}, 'sig', '0.1')
        self.assertEqual(self.uuid, val.uuid)
        self.assertEqual('abc123', val.key)
        self.assertEqual('value', val.value)
        self.assertEqual(1350544046.084875, val.timestamp)
        self.assertEqual('abcdefg', val.public_key)
        self.assertEqual('name', val.name)
        self.assertEqual({'meta': 'value'}, val.meta)
        self.assertEqual('sig', val.sig)
        self.assertEqual('0.1', val.version)


class TestMessagePackConversion(unittest.TestCase):
    """
    Ensures functions for encoding and decoding messages in to and from
    MessagePack strings to message objects work as expected.
    """

    def setUp(self):
        """
        Gives us some messages to play with.
        """
        self.uuid = str(uuid4())
        self.value = 1.234
        self.timestamp = time.time()
        self.public_key = PUBLIC_KEY
        self.name = 'a_human_readable_key_name'
        self.key = construct_key(self.public_key, self.name)
        self.meta = {
            'mime': 'numeric',
            'description': 'a test value'
        }
        self.sig = generate_signature(self.value, self.timestamp, self.name,
            self.meta, PRIVATE_KEY)
        self.version = '0.1'
        self.message = 'value'
        self.nodes = (('hash1', '127.0.0.1', 1908), ('hash2', '0.0.0.0', 1908))
        self.mock_message = Value(self.uuid, self.key, self.value,
            self.timestamp, self.public_key, self.name, self.meta, self.sig,
            self.version)

    def test_to_msgpack(self):
        """
        Simple good case.
        """
        result = to_msgpack(self.mock_message)
        unpacked = msgpack.unpackb(result)
        for k in ['uuid', 'key', 'value', 'timestamp', 'public_key', 'name',
            'meta', 'sig', 'version', 'message']:
            self.assertIn(k, unpacked.keys())
            self.assertEqual(unpacked[k], getattr(self, k))

    def test_from_msgpack_error(self):
        """
        Ensures a valid error message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'error',
            'uuid': self.uuid,
            'code': 1,
            'title': ERRORS[1],
            'details': {'key': 'value'},
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Error)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.code, 1)
        self.assertEqual(result.title, ERRORS[1])
        self.assertEqual(result.details, {'key': 'value'})
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_ping(self):
        """
        Ensures a valid ping message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'ping',
            'uuid': self.uuid,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Ping)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_pong(self):
        """
        Ensures a valid pong message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'pong',
            'uuid': self.uuid,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Pong)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_store(self):
        """
        Ensures a valid store message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'store',
            'uuid': self.uuid,
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp,
            'public_key': self.public_key,
            'name': self.name,
            'meta': self.meta,
            'sig': self.sig,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Store)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.value, self.value)
        self.assertEqual(result.timestamp, self.timestamp)
        self.assertEqual(result.public_key, self.public_key)
        self.assertEqual(result.name, self.name)
        self.assertEqual(result.meta, self.meta)
        self.assertEqual(result.sig, self.sig)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_findnode(self):
        """
        Ensures a valid findnode message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'findnode',
            'uuid': self.uuid,
            'key': self.key,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, FindNode)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_nodes(self):
        """
        Ensures a valid nodes message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'nodes',
            'uuid': self.uuid,
            'nodes': self.nodes,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Nodes)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.nodes, self.nodes)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_findvalue(self):
        """
        Ensures a valid findvalue message is correctly parsed.
        """
        mock_message = msgpack.packb({
            'message': 'findvalue',
            'uuid': self.uuid,
            'key': self.key,
            'version': self.version
        })
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, FindValue)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_value(self):
        """
        Ensures a valid value message is correctly parsed.
        """
        mock_message = to_msgpack(self.mock_message)
        result = from_msgpack(mock_message)
        self.assertIsInstance(result, Value)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.value, self.value)
        self.assertEqual(result.timestamp, self.timestamp)
        self.assertEqual(result.public_key, self.public_key)
        self.assertEqual(result.name, self.name)
        self.assertEqual(result.meta, self.meta)
        self.assertEqual(result.sig, self.sig)
        self.assertEqual(result.version, self.version)

    def test_from_msgpack_unknown_request(self):
        """
        Ensures the correct exception is raised if the message is not
        recognised.
        """
        # "pang" is "bang" in Swedish (apparently).
        mock_message = msgpack.packb({
            'message': 'pang',
            'uuid': self.uuid,
            'version': self.version
        })
        with self.assertRaises(ValueError) as cm:
            result = from_msgpack(mock_message)
        ex = cm.exception
        self.assertEqual(2, ex.args[0])
        self.assertEqual(ERRORS[2], ex.args[1])
        self.assertEqual('pang is not a valid message type.',
            ex.args[2]['context'])


class TestMakeMessage(unittest.TestCase):
    """
    Ensures that the make_message function performs as expected.
    """

    def test_make_message(self):
        """
        The good case returns an instance of the given class based upon the
        data provided.
        """
        uuid = str(uuid4())
        result = make_message(Ping, {'uuid': uuid, 'version': '0.1'})
        self.assertIsInstance(result, Ping)
        self.assertEqual(uuid, result.uuid)
        self.assertEqual('0.1', result.version)

    def test_make_message_bad_values(self):
        """
        The values to be used to instantiate the class should be valid. If not
        the correct exception is raised.
        """
        with self.assertRaises(ValueError) as cm:
            result = make_message(Ping, {'uuid': 1, 'version': 2})
        ex = cm.exception
        self.assertEqual(2, ex.args[0])
        self.assertEqual(ERRORS[2], ex.args[1])
        details = ex.args[2]
        self.assertEqual('Invalid value.', details['uuid'])
        self.assertEqual('Invalid value.', details['version'])

    def test_make_message_missing_fields(self):
        """
        The correct fields must all exist in the provided data dictionary.
        """
        with self.assertRaises(ValueError) as cm:
            result = make_message(Ping, {'foo': 1, 'bar': 2})
        ex = cm.exception
        self.assertEqual(2, ex.args[0])
        self.assertEqual(ERRORS[2], ex.args[1])
        details = ex.args[2]
        self.assertEqual('Missing field.', details['uuid'])
        self.assertEqual('Missing field.', details['version'])
