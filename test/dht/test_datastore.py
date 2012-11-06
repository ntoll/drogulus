"""
Ensures datastore related classes work as expected.
"""
from drogulus.dht.datastore import DataStore, DictDataStore
from drogulus.dht.messages import Value
from drogulus.dht.crypto import construct_key, generate_signature
import unittest
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


class TestDataStore(unittest.TestCase):
    """
    Ensures the base class is defined as expected (no functionality is built
    in to the class). Basically, a bunch of trivial sanity tests.
    """

    def test_keys(self):
        """
        Check the DataStore base class has a keys method.
        """
        self.assertTrue(hasattr(DataStore, 'keys'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.keys())

    def test_last_published(self):
        """
        Check the DataStore base class has a last_published method.
        """
        self.assertTrue(hasattr(DataStore, 'last_published'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.last_published(123))

    def test_original_publisher_id(self):
        """
        Check the DataStore base class has an original_publisher_id method.
        """
        self.assertTrue(hasattr(DataStore, 'original_publisher_id'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.original_publisher_id(123))

    def test_set_item(self):
        """
        Check the DataStore base class has a set_item method.
        """
        self.assertTrue(hasattr(DataStore, 'set_item'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.set_item(123, 'value'))

    def test__getitem__(self):
        """
        Check the DataStore base class has a __getitem__ method.
        """
        self.assertTrue(hasattr(DataStore, '__getitem__'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds['item'])

    def test__setitem__(self):
        """
        Check the DataStore base class has a __setitem__ method.
        """
        self.assertTrue(hasattr(DataStore, '__setitem__'))

    def testDelete(self):
        """
        Check the DataStore base class has a __delitem__ method.
        """
        self.assertTrue(hasattr(DataStore, '__delitem__'))


class TestDictDataStore(unittest.TestCase):
    """
    Ensures that the in-memory Python dict based data store works as expected.
    """

    def setUp(self):
        """
        A message to play with.
        """
        self.uuid = str(uuid4())
        self.value = 1.234
        self.timestamp = time.time()
        self.expires = self.timestamp + 1000
        self.public_key = PUBLIC_KEY
        self.name = 'a_human_readable_key_name'
        self.key = construct_key(self.public_key, self.name)
        self.meta = {
            'mime': 'numeric',
            'description': 'a test value'
        }
        self.sig = generate_signature(self.value, self.timestamp, self.expires,
                                      self.name, self.meta, PRIVATE_KEY)
        self.version = '0.1'
        self.message = 'value'
        self.mock_value = Value(self.uuid, self.key, self.value,
                                self.timestamp, self.expires, self.public_key,
                                self.name, self.meta, self.sig, self.version)

    def test__init__(self):
        """
        Ensures the DictDataStore is instantiated to an expected state.
        """
        store = DictDataStore()
        self.assertTrue(hasattr(store, '_dict'))
        self.assertEqual({}, store._dict)

    def test_keys(self):
        """
        Ensure the keys method works as expected.
        """
        store = DictDataStore()
        self.assertEqual([], store.keys())
        store['foo'] = self.mock_value
        self.assertTrue('foo' in store.keys())

    def test_last_published(self):
        """
        Ensures the correct value is returned from last_published for a given
        key.
        """
        store = DictDataStore()
        store['foo'] = self.mock_value
        self.assertTrue(store.last_published('foo'))

    def test_original_publisher_id(self):
        """
        Ensures the correct value is returned from original_publisher_id for a
        given key.
        """
        store = DictDataStore()
        store['foo'] = self.mock_value
        self.assertEqual(self.public_key, store.original_publisher_id('foo'))

    def test_original_publish_time(self):
        """
        Ensures the correct value is returned from original_publish_time for a
        given key.
        """
        store = DictDataStore()
        store['foo'] = self.mock_value
        self.assertEqual(self.timestamp, store.original_publish_time('foo'))

    def test_set_item(self):
        """
        Ensures that the set_item method works as expected.
        """
        store = DictDataStore()
        store.set_item('foo', self.mock_value)
        self.assertEqual(1, len(store.keys()))
        self.assertEqual('foo', store.keys()[0])
        self.assertEqual(self.mock_value, store['foo'])

    def test__getitem__(self):
        """
        Ensures that the __getitem__ method works as expected.
        """
        store = DictDataStore()
        store.set_item('foo', self.mock_value)
        self.assertEqual(self.mock_value, store['foo'])

    def test__delitem__(self):
        """
        Ensures that the __delitem__ method works as expected.
        """
        store = DictDataStore()
        store.set_item('foo', self.mock_value)
        self.assertEqual(1, len(store.keys()))
        del store['foo']
        self.assertEqual(0, len(store.keys()))
