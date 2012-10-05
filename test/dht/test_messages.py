"""
A set of sanity checks to ensure that the messages are defined as expected.
"""
from drogulus.dht.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
    FindValue, Value, generate_signature, validate_signature,
    validate_key_value, construct_hash, construct_key)
import unittest
import hashlib
import msgpack
from datetime import datetime


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


class TestMessages(unittest.TestCase):
    """
    Ensures the message classes are *defined* as expected and the relevant
    fields can be indexed.
    """

    def test_error(self):
        """
        Expected behaviour of an error message.
        """
        error = Error(1, 2, 'This is an error', {'foo': 'bar'}, 0.1)
        self.assertEqual(1, error.id)
        self.assertEqual(2, error.code)
        self.assertEqual('This is an error', error.title)
        self.assertEqual({'foo': 'bar'}, error.details)
        self.assertEqual(0.1, error.version)

    def test_ping(self):
        """
        Expected behaviour of a ping message.
        """
        ping = Ping(1, 0.1)
        self.assertEqual(1, ping.id)
        self.assertEqual(0.1, ping.version)

    def test_pong(self):
        """
        Expected behaviour of a pong message.
        """
        pong = Pong(1, 0.1)
        self.assertEqual(1, pong.id)
        self.assertEqual(0.1, pong.version)

    def test_store(self):
        """
        Expected behaviour of a store message.
        """
        store = Store(1, 2, 'value', '12345', 'abcdefg', 'name', 'meta', 'sig',
            0.1)
        self.assertEqual(1, store.id)
        self.assertEqual(2, store.key)
        self.assertEqual('value', store.value)
        self.assertEqual('12345', store.time)
        self.assertEqual('abcdefg', store.public_key)
        self.assertEqual('name', store.name)
        self.assertEqual('sig', store.sig)
        self.assertEqual(0.1, store.version)

    def test_find_node(self):
        """
        Expected behaviour of a findnode message.
        """
        fn = FindNode(1, 'key', 0.1)
        self.assertEqual(1, fn.id)
        self.assertEqual('key', fn.key)
        self.assertEqual(0.1, fn.version)

    def test_nodes(self):
        """
        Expected behaviour of a nodes message.
        """
        nodes = Nodes(1, [('127.0.0.1', 1908)], 0.1)
        self.assertEqual(1, nodes.id)
        self.assertEqual([('127.0.0.1', 1908)], nodes.nodes)
        self.assertEqual(0.1, nodes.version)

    def test_find_value(self):
        """
        Expected behaviour of a findvalue message.
        """
        fv = FindValue(1, 'key', 0.1)
        self.assertEqual(1, fv.id)
        self.assertEqual('key', fv.key)
        self.assertEqual(0.1, fv.version)

    def test_value(self):
        """
        Expected behaviour of a value message.
        """
        val = Value(1, 2, 'value', '12345', 'abcdefg', 'name', 'meta', 'sig',
            0.1)
        self.assertEqual(1, val.id)
        self.assertEqual(2, val.key)
        self.assertEqual('value', val.value)
        self.assertEqual('12345', val.time)
        self.assertEqual('abcdefg', val.public_key)
        self.assertEqual('name', val.name)
        self.assertEqual('sig', val.sig)
        self.assertEqual(0.1, val.version)

    def test_generate_signature(self):
        """
        Ensures that the given values result in the expected signature
        given a certain private key and said signature can be validated with
        the related public key.
        """
        expected = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        actual = generate_signature('value', '1234', 'name', 'meta',
            PRIVATE_KEY)
        self.assertEqual(expected, actual)
        # Check the resulting signature can be validated with the public key
        check = validate_signature('value', '1234', 'name', 'meta', expected,
            PUBLIC_KEY)
        self.assertEqual(True, check)

    def test_validate_signature(self):
        """
        Ensures that given some values and an associated valid signature the
        validate_signature returns True for the correct public key.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        check = validate_signature('value', '1234', 'name', 'meta', signature,
            PUBLIC_KEY)
        self.assertEqual(True, check)

    def test_validate_signature_bad_sig(self):
        """
        Ensures that an in valid signature results in a False.
        """
        signature = 'helloworld'
        check = validate_signature('value', '1234', 'name', 'meta', signature,
            PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_signature_bad_public_key(self):
        """
        Ensures that given a valid signature but wrong public key, validation
        results in False.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        check = validate_signature('value', '1234', 'name', 'meta', signature,
            BAD_PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_signature_wrong_public_key(self):
        """
        Ensures that given a valid signature but wrong public key, validation
        results in False.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        check = validate_signature('value', '1234', 'name', 'meta', signature,
            ALT_PUBLIC_KEY)
        self.assertEqual(False, check)

    def test_validate_key_value_good(self):
        """
        Ensures the verify_message function returns True for a valid message.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (True, None)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_wrong_value(self):
        """
        Ensures the verify_message function returns False if the message's
        value field has been altered.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'bad_value', '1234', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_wrong_time(self):
        """
        Ensures the verify_message function returns False if the message's
        time field has been altered.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '4321', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_wrong_name(self):
        """
        Ensures the verify_message function returns False if the message's
        name field has been altered.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'bad_name', 'meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_wrong_meta(self):
        """
        Ensures the verify_message function returns False if the message's
        meta field has been altered.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'name', 'bad_meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_bad_public_key(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of a bad public key.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', ALT_PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_validate_key_value_bad_sig(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of a bad signature.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08'
        key = construct_key(PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 6)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_verify_message_bad_key_from_public_key(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of an incorrect 'key' value with wrong public key
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(ALT_PUBLIC_KEY, 'name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 7)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_verify_message_bad_key_from_name(self):
        """
        Ensure the correct result is returned if the message is invalid
        because of an incorrect 'key' value with wrong name.
        """
        signature = 'N\xb0V?\x89\xfbXe \x88^<\x9a\x98\xb9\xbe\xf8m\xe52>\xe0\xb9B\x9a\xe4s-\xdc\xe7ICH\xfee\xf9\x1e*\x9b\xbe\xb4\xea\x8e~@\x93F~!\x1f\xa6\t\x0c\xda\xb9\xc9\x97\xbc_\xb3\x98\xb8R\xde\xfeD]\xc9 \xf8\xdc7\xa2\xc9Vx\x89i\x1b\xef\x8c;\xe4F\xe7YZ\xb5\xa4D\x9c\x82M<TIk\x99\x1d\x1b\xbf7I\x99S~\xd4-\xa1\xf4(\xcc\x9d\x11\xbc\xc9\n\x877\xa9\x08*3O\xed\r\xa4\xbd'
        key = construct_key(PUBLIC_KEY, 'wrong_name')
        val = Value(1, key, 'value', '1234', PUBLIC_KEY, 'name', 'meta',
            signature, 0.1)
        expected = (False, 7)
        actual = validate_key_value(key, val)
        self.assertEqual(expected, actual)

    def test_construct_hash(self):
        """
        Ensures that the hash is correctly generated.
        """
        value = 'foo'
        time = datetime.now().isoformat()
        name = 'bar'
        meta = {'baz': 'qux'}
        hashes = []
        for item in (value, time, name, meta):
            packed = msgpack.packb(item)
            hasher = hashlib.sha1()
            hasher.update(packed)
            hashes.append(hasher.hexdigest())
        compound_hashes = ''.join(hashes)
        hasher = hashlib.sha1()
        hasher.update(compound_hashes)
        expected = hasher.hexdigest()
        actual = construct_hash(value, time, name, meta)
        self.assertEqual(expected, actual.hexdigest())

    def test_construct_key(self):
        """
        Ensures that a DHT key is constructed correctly given correct inputs.
        """
        name = 'foo/bar.baz'
        pk_hasher = hashlib.sha1()
        pk_hasher.update(PUBLIC_KEY)
        pk_hash = pk_hasher.hexdigest()
        name_hasher = hashlib.sha1()
        name_hasher.update(name)
        name_hash = name_hasher.hexdigest()
        hasher = hashlib.sha1()
        hasher.update(pk_hash + name_hash)
        expected = hasher.hexdigest()
        actual = construct_key(PUBLIC_KEY, name)
        self.assertEqual(expected, actual)

    def test_construct_key_empty_name(self):
        """
        Ensures that a DHT key is constructed given only the public key.
        """
        pk_hasher = hashlib.sha1()
        pk_hasher.update(PUBLIC_KEY)
        expected = pk_hasher.hexdigest()
        actual = construct_key(PUBLIC_KEY)
        self.assertEqual(expected, actual)
