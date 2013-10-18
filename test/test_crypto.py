# -*- coding: utf-8 -*-
"""
A set of sanity checks to ensure that the messages are defined as expected.
"""
from drogulus.crypto import (generate_signature, validate_signature,
                             validate_message, construct_hash,
                             construct_key)
from drogulus.net.messages import Value
import unittest
import hashlib
import msgpack
import time


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


BAD_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
HELLOA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+n3Au1cbSkjCVsrfnTbmA0SwQ
LN2RbbDIMHILA1i6wByXkqEamnEBvgsOkUUrsEXYtt0vb8Qill4LSs9RqTetSCjG
b+oGVTKizfbMbGCKZ8fT64ZZgan9TvhItl7DAwbIXcyvQ+b1J7pHaytAZwkSwh+M
6WixkMTbFM91fW0mUwIDAQAB
-----END PUBLIC KEY-----"""


ALT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxec+GS3c3qzE4WgKoQMJ
GgBJG/0oOdRb6UKnqJ6p3/vb9iw//OqMbLYCYKtU4JfaTritjwNd0bWhMa4Q09Jc
z2fL9uG1j/d66iasGWooEpBICzBPiao7rQYtxbHzoUV+a1jzv7HcEQrdBYbGEbSc
A1o8gbMAj4oMh+neJFPxHKLxMHMPEW+lmPvFGcUIVUOyvZl0mAn5PSJnXOenB9Zg
tG/zEXoI+YfPpSQ6CgAFU1JFRMCXEAvr/lSkSKN6uGeu2bZDWT597Qddc+DI+XFW
39pEBxh2H59WNiK1f/DRBvgGUgBrCZAxyTwrjE9fi/1z0lFRw9pH7V6SaJtK1KWh
WQIDAQAB
-----END PUBLIC KEY-----"""


class TestMessageCryptoFunctions(unittest.TestCase):
    """
    Ensures that functions for signing and validating messages work as
    expected.
    """

    def setUp(self):
        """
        Set some values used in all tests.
        """
        self.signature = ('\x80 \xf6\x155\x93Z\xdf1t*\xc6\xc8b\x9b~\xc0\xa6' +
                          '\xf8\xa7\xc0\xd5\x91\xa2Q\xd7\\\xd1\x1a\x0eX' +
                          '\x855>\xc4\xa3\xa1l\xe26\x9d\x94\x9f\x92\t\xf8' +
                          '\x8f\xe6iblp\x84}\x0cc(\xb7c\xba\x97J\x87u\x9f' +
                          '\xd6\x1a]A\x870\x1df\xe8i\xe8\xbe\xf2\xc6\x8f' +
                          '\xd0\x8f\xd18\xb8\\\xbc\x01\x1a\x1fP\xd6I\x06' +
                          '\xf3K\xb1\x1e@\xc4ma61\xd4\x12\xf4!\x9dm3\x01n' +
                          '\x17\xbcr\xe0\xf4Y-\xc7=\x87\xc4Xv\x84\xfa')
        self.value = 'value'
        self.timestamp = 1350544046.084875
        self.expires = 1352221970.14242
        self.name = 'name'
        self.meta = {'meta': 'value'}
        self.version = '0.1'
        self.key = construct_key(PUBLIC_KEY, self.name)

    def test_generate_signature(self):
        """
        Ensures that the given values result in the expected signature
        given a certain private key and said signature can be validated with
        the related public key.
        """
        expected = self.signature
        actual = generate_signature(self.value, self.timestamp, self.expires,
                                    self.name, self.meta, self.version,
                                    PRIVATE_KEY)
        self.assertEqual(expected, actual)
        # Check the resulting signature can be validated with the public key
        check = validate_signature(self.value, self.timestamp, self.expires,
                                   self.name, self.meta, self.version,
                                   expected, PUBLIC_KEY)
        self.assertEqual(True, check)

    def test_validate_signature(self):
        """
        Ensures that given some values and an associated valid signature the
        validate_signature returns True for the correct public key.
        """
        check = validate_signature(self.value, self.timestamp, self.expires,
                                   self.name, self.meta, self.version,
                                   self.signature, PUBLIC_KEY)
        self.assertEqual(True, check)

    def test_validate_signature_bad_sig(self):
        """
        Ensures that an invalid signature results in a False.
        """
        signature = 'helloworld'
        check = validate_signature(self.value, self.timestamp, self.expires,
                                   self.name, self.meta, self.version,
                                   signature, PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_signature_bad_public_key(self):
        """
        Ensures that given a valid signature but wrong public key, validation
        results in False.
        """
        check = validate_signature(self.value, self.timestamp, self.expires,
                                   self.name, self.meta, self.version,
                                   self.signature, BAD_PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_signature_wrong_public_key(self):
        """
        Ensures that given a valid signature but wrong public key, validation
        results in False.
        """
        check = validate_signature(self.value, self.timestamp, self.expires,
                                   self.name, self.meta, self.version,
                                   self.signature, ALT_PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_message_good(self):
        """
        Ensures the validate_message function returns True for a valid message.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (True, None)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_value(self):
        """
        Ensures the validate_message function returns False if the message's
        value field has been altered.
        """
        val = Value(1, 1, self.key, 'bad_value', self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_timestamp(self):
        """
        Ensures the validate_message function returns False if the message's
        timestamp field has been altered.
        """
        val = Value(1, 1, self.key, self.value, 1350544046.084876,
                    self.expires, self.version, PUBLIC_KEY, self.name,
                    self.meta, self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_expires(self):
        """
        Ensures the validate_message function returns False if the message's
        expires field has been altered.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, 0.0,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_created_with(self):
        """
        Ensures the validate_message function returns False if the message's
        created_with field has been altered.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    '1.1.foo', PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_name(self):
        """
        Ensures the validate_message function returns False if the message's
        name field has been altered.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, 'bad_name', self.meta,
                    self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_wrong_meta(self):
        """
        Ensures the validate_message function returns False if the message's
        meta field has been altered.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name,
                    {'bad_meta': 'value'}, self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_bad_public_key(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of a bad public key.
        """
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    self.version, ALT_PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_bad_sig(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of a bad signature.
        """
        bad_signature = ('\x1c\x10s\x1b\x83@r\x11\x83*2\xa1l\x0f\xba*\xd7C' +
                         '\xd4\xa7\x07\xe3\x90\xcc\xc4\x16\xe9 \xadg\x03\xbf' +
                         '\x9c\\\xe2\xfe\x88\xdb\\=,-\xd1/\xa9I2\xc2S\xe7' +
                         '\x07c\xf9X%\x1c\x939\xe6\xa8\x10_\xf3\xeeRlj\xc5i~' +
                         '\x94\xcd\xbd\xb24ujq\xa9Nw\xd0\xad\xa7\xde_\x9cpxj' +
                         '\xdd\x8a\xe8\xfd\xaf\xcbRn\xb7C\xb1q\x13c\xc9' +
                         '\x89@w\xac\xc4\xf8\x87\x9ct\x1a\xa6')
        val = Value(1, 1, self.key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    bad_signature, self.version)
        expected = (False, 6)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_bad_key_from_public_key(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of an incorrect 'key' value with wrong public key
        """
        key = construct_key(ALT_PUBLIC_KEY, 'name')
        val = Value(1, 1, key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 7)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_validate_message_bad_key_from_name(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of an incorrect 'key' value with wrong name.
        """
        key = construct_key(PUBLIC_KEY, 'wrong_name')
        val = Value(1, 1, key, self.value, self.timestamp, self.expires,
                    self.version, PUBLIC_KEY, self.name, self.meta,
                    self.signature, self.version)
        expected = (False, 7)
        actual = validate_message(val)
        self.assertEqual(expected, actual)

    def test_construct_hash(self):
        """
        Ensures that the hash is correctly generated.
        """
        value = 'foo'
        timestamp = time.time()
        expires = timestamp + 1000
        name = 'bar'
        meta = {'baz': 'qux'}
        created_with = '0.0.0.alpha.0'
        hashes = []
        for item in (value, timestamp, expires, name, meta, created_with):
            packed = msgpack.packb(item)
            hasher = hashlib.sha512()
            hasher.update(packed)
            hashes.append(hasher.digest())
        compound_hashes = ''.join(hashes)
        hasher = hashlib.sha512()
        hasher.update(compound_hashes)
        expected = hasher.digest()
        actual = construct_hash(value, timestamp, expires, name, meta,
                                created_with)
        self.assertEqual(expected, actual.digest())

    def test_construct_key(self):
        """
        Ensures that a DHT key is constructed correctly given correct inputs.
        """
        name = 'foo/bar.baz'
        pk_hasher = hashlib.sha512()
        pk_hasher.update(PUBLIC_KEY)
        pk_hash = pk_hasher.digest()
        name_hasher = hashlib.sha512()
        name_hasher.update(name)
        name_hash = name_hasher.digest()
        hasher = hashlib.sha512()
        hasher.update(pk_hash + name_hash)
        expected = hasher.digest()
        actual = construct_key(PUBLIC_KEY, name)
        self.assertEqual(expected, actual)

    def test_construct_key_empty_name(self):
        """
        Ensures that a DHT key is constructed given only the public key.
        """
        pk_hasher = hashlib.sha512()
        pk_hasher.update(PUBLIC_KEY)
        expected = pk_hasher.digest()
        actual = construct_key(PUBLIC_KEY)
        self.assertEqual(expected, actual)
