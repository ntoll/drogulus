# -*- coding: utf-8 -*-
"""
Ensures the cryptographic signing and related functions work as expected.
"""
from drogulus.dht.crypto import (get_seal, check_seal, get_signed_item,
                                 verify_item, _get_hash, construct_key)
from drogulus.dht.messages import Ping
from drogulus.version import get_version
from hashlib import sha512
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from .keys import PRIVATE_KEY, PUBLIC_KEY, BAD_PUBLIC_KEY
import unittest
import uuid
import base64


class TestGetSeal(unittest.TestCase):
    """
    Ensures valid seals are created.
    """

    def test_get_seal(self):
        """
        Ensure a good "seal" is created for the passed in dict of values
        given the supplied private key and appropriate shared public key to
        be used to validate the seal.
        """
        values = {
            'foo': 'bar',
            'baz': {
                'a': 1,
                'b': True,
                'c': 3.141,
                'd': [1, 2, 3]
            },
        }
        seal = get_seal(values, PRIVATE_KEY)
        self.assertIsInstance(seal, str)
        # Check it's a seal that can be validated with the correct public key.
        sig = base64.decodebytes(seal.encode('utf-8'))
        public_key = RSA.importKey(PUBLIC_KEY)
        root_hash = _get_hash(values)
        verifier = PKCS1_v1_5.new(public_key)
        self.assertTrue(verifier.verify(root_hash, sig))


class TestCheckSeal(unittest.TestCase):
    """
    Ensures seals are checked and validated correctly.
    """

    def test_check_seal(self):
        """
        Make sure message objects that contain a valid seal are correctly
        checked.
        """
        ping_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': PUBLIC_KEY,
            'reply_port': 1908,
            'version': get_version()
        }
        seal = get_seal(ping_dict, PRIVATE_KEY)
        ping = Ping(ping_dict['uuid'], ping_dict['recipient'],
                    ping_dict['sender'], ping_dict['reply_port'],
                    ping_dict['version'], seal)
        self.assertTrue(check_seal(ping))

    def test_check_seal_invalid_seal(self):
        """
        Ensure a message with an invalid seal fails the check.
        """
        ping_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': BAD_PUBLIC_KEY,
            'reply_port': 1908,
            'version': get_version()
        }
        seal = get_seal(ping_dict, PRIVATE_KEY)
        ping = Ping(ping_dict['uuid'], ping_dict['recipient'],
                    ping_dict['sender'], ping_dict['reply_port'],
                    ping_dict['version'], seal)
        self.assertFalse(check_seal(ping))

    def test_check_seal_bad_seal(self):
        """
        Ensure a message with a bad seal (i.e. malformed junk) fails the check.
        """
        ping_dict = {
            'uuid': str(uuid.uuid4()),
            'recipient': PUBLIC_KEY,
            'sender': BAD_PUBLIC_KEY,
            'reply_port': 1908,
            'version': get_version()
        }
        seal = 'not a seal'
        ping = Ping(ping_dict['uuid'], ping_dict['recipient'],
                    ping_dict['sender'], ping_dict['reply_port'],
                    ping_dict['version'], seal)
        self.assertFalse(check_seal(ping))


class TestGetSignedItem(unittest.TestCase):
    """
    Ensures the drogulus.dht.crypto._get_signed_value function works as
    expected.
    """

    def test_expected_metadata(self):
        """
        Ensure the item (dict) returned from the function contains the
        expected metadata.
        """
        key = 'key'
        value = 'value'
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY)
        self.assertIn('timestamp', signed_item)
        self.assertIsInstance(signed_item['timestamp'], float)
        self.assertIn('expires', signed_item)
        self.assertIsInstance(signed_item['expires'], float)
        self.assertIn('created_with', signed_item)
        self.assertEqual(signed_item['created_with'], get_version())
        self.assertIn('public_key', signed_item)
        self.assertEqual(signed_item['public_key'], PUBLIC_KEY)
        self.assertIn('signature', signed_item)
        self.assertIsInstance(signed_item['signature'], str)
        self.assertIn('key', signed_item)
        self.assertIsInstance(signed_item['key'], str)
        self.assertEqual(signed_item['key'], construct_key(PUBLIC_KEY, key))
        self.assertEqual(signed_item['name'], key)
        self.assertEqual(signed_item['value'], value)

    def test_expires(self):
        """
        Ensure the expires argument is handled and checked appropriately.

        * If it's not passed the expires metadata defaults to 0.0.
        * It must be a number (int or float).
        * It must be > 0
        * The "expires" metadata must == timestamp + passed in expires arg.
        """
        key = 'key'
        value = 'value'
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY)
        self.assertEqual(0.0, signed_item['expires'])
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY,
                                      'foo')
        self.assertEqual(0.0, signed_item['expires'])
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY,
                                      123)
        self.assertEqual(signed_item['timestamp'] + 123,
                         signed_item['expires'])
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY,
                                      123.456)
        self.assertEqual(signed_item['timestamp'] + 123.456,
                         signed_item['expires'])
        signed_item = get_signed_item(key, value, PUBLIC_KEY, PRIVATE_KEY,
                                      -1)
        self.assertEqual(0.0, signed_item['expires'])

    def test_signed_item_is_verifiable(self):
        """
        Check that the resulting item is able to be verified.
        """
        signed_item = get_signed_item('key', 'value', PUBLIC_KEY,
                                      PRIVATE_KEY)
        self.assertTrue(verify_item(signed_item))


class TestVerifyItem(unittest.TestCase):
    """
    Ensures the drogulus.dht.crypto.verify_item function works as expected.
    """

    def test_good_item(self):
        """
        The good case should pass.
        """
        signed_item = get_signed_item('key', 'value', PUBLIC_KEY, PRIVATE_KEY)
        self.assertTrue(verify_item(signed_item))

    def test_malformed_item(self):
        """
        Does not contain the expected metadata.
        """
        item = {
            'foo': 'bar',
            'baz': [1, 2, 3]
        }
        self.assertFalse(verify_item(item))

    def test_modified_item(self):
        """
        The content of the item does not match the hash / signature.
        """
        signed_item = get_signed_item('key', 'value', PUBLIC_KEY, PRIVATE_KEY)
        signed_item['public_key'] = BAD_PUBLIC_KEY
        self.assertFalse(verify_item(signed_item))


class TestGetHashFunction(unittest.TestCase):
    """
    Ensures the drogulus.dht.crypto._get_hash function works as expected.
    """

    def test_get_hash_dict(self):
        """
        Ensures that the dict is hashed in such a way that the keys are
        sorted so the resulting leaf hashes are used in the correct order.
        """
        to_hash = {}
        for i in range(5):
            k = str(uuid.uuid4())
            v = str(uuid.uuid4())
            to_hash[k] = v

        seed_hashes = []
        for k in sorted(to_hash):
            v = to_hash[k]
            seed_hashes.append(sha512(k.encode('utf-8')).hexdigest())
            seed_hashes.append(sha512(v.encode('utf-8')).hexdigest())
        seed = ''.join(seed_hashes)
        expected = sha512(seed.encode('utf-8'))
        actual = _get_hash(to_hash)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_list(self):
        """
        Ensure all the items in a list are hashed in the correct order.
        """
        to_hash = []
        for i in range(5):
            to_hash.append(str(uuid.uuid4()))

        seed_hashes = []
        for item in to_hash:
            seed_hashes.append(sha512(item.encode('utf-8')).hexdigest())
        seed = ''.join(seed_hashes)
        expected = sha512(seed.encode('utf-8'))
        actual = _get_hash(to_hash)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_none(self):
        """
        Ensure the hash of Python's None is actually a hash of 'null' (since
        this is the null value for JSON).
        """
        expected = sha512(b'null')
        actual = _get_hash(None)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_boolean_true(self):
        """
        Ensure hash of Python's True boolean value is a hash of 'true' (since
        this is the true value in JSON).
        """
        expected = sha512(b'true')
        actual = _get_hash(True)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_boolean_false(self):
        """
        Ensure hash of Python's False boolean value is a hash of 'false'
        (since this is the false value in JSON).
        """
        expected = sha512(b'false')
        actual = _get_hash(False)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_float(self):
        """
        Ensure float values are hashed correctly.
        """
        expected = sha512(b'12345.6789')
        actual = _get_hash(12345.6789)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_int(self):
        """
        Ensure integer values are hashed correctly.
        """
        expected = sha512(b'1234567890987654321234567890987654321')
        actual = _get_hash(1234567890987654321234567890987654321)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_str(self):
        """
        Strings are hashed correctly
        """
        expected = sha512(b'foo')
        actual = _get_hash('foo')
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_get_hash_nested_structure(self):
        """
        Ensure a tree like object is recursively hashed to produce a root-hash
        value.
        """
        child_list = ['bar', 1, 1.234, ]
        child_dict = {
            'b': False,
            'a': None,
            'c': True
        }
        to_hash = {
            'foo': child_list,
            'baz': child_dict
        }
        seed_hashes = []
        # REMEMBER - in this algorithm the keys to a dict object are ordered.
        seed_hashes.append(sha512(b'baz').hexdigest())
        seed_hashes.append(_get_hash(child_dict).hexdigest())
        seed_hashes.append(sha512(b'foo').hexdigest())
        seed_hashes.append(_get_hash(child_list).hexdigest())
        seed = ''.join(seed_hashes)
        expected = sha512(seed.encode('utf-8'))
        actual = _get_hash(to_hash)
        self.assertEqual(expected.hexdigest(), actual.hexdigest())


class TestConstructKey(unittest.TestCase):
    """
    Ensures the construct_key function works as expected.
    """

    def test_compound_key(self):
        """
        Ensures the DHT key is constructed correctly given appropriate inputs.
        """
        name = 'foo'
        pk_hasher = sha512(PUBLIC_KEY.encode('ascii'))
        name_hasher = sha512(name.encode('utf-8'))
        hasher = sha512(pk_hasher.digest() + name_hasher.digest())
        expected = hasher.hexdigest()
        actual = construct_key(PUBLIC_KEY, name)
        self.assertEqual(expected, actual)

    def test_no_name(self):
        """
        Ensures the DHT key is correct given only a public_key argument.
        """
        pk_hasher = sha512(PUBLIC_KEY.encode('ascii'))
        expected = pk_hasher.hexdigest()
        actual = construct_key(PUBLIC_KEY)
        self.assertEqual(expected, actual)
