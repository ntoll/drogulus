# -*- coding: utf-8 -*-
"""
Ensures datastore related classes work as expected.
"""
import unittest
import time
from drogulus.dht.storage import DataStore, DictDataStore
from unittest.mock import MagicMock
from .keys import PUBLIC_KEY


class TestDataStore(unittest.TestCase):
    """
    Ensures that the functionality built into the base class works as
    expected.
    """

    def test_keys(self):
        """
        Check the DataStore base class has a keys method.
        """
        self.assertTrue(hasattr(DataStore, 'keys'))
        ds = DataStore()
        self.assertRaises(NotImplementedError, ds.keys)

    def test_updated(self):
        """
        Check the DataStore base class gets the requested item and returns the
        timestamp in position 1 of the tuple.
        """
        self.assertTrue(hasattr(DataStore, 'updated'))
        ds = DataStore()
        timestamp = time.time()
        ds._get_item = MagicMock(return_value=(None, timestamp, None))
        result = ds.updated('foo')
        self.assertEqual(timestamp, result)
        ds._get_item.assert_called_once_with('foo')

    def test_publisher(self):
        """
        Check the DataStore base class gets the requested item and returns the
        public key of the publisher associated with the item.
        """
        self.assertTrue(hasattr(DataStore, 'publisher'))
        ds = DataStore()
        val = {
            'public_key': PUBLIC_KEY
        }
        ds._get_item = MagicMock(return_value=(val, None, None))
        result = ds.publisher('foo')
        self.assertEqual(PUBLIC_KEY, result)
        ds._get_item.assert_called_once_with('foo')

    def test_created(self):
        """
        Check the DataStore base class gets the requested item and returns the
        creation timestamp that the publisher has associated with the item.
        """
        self.assertTrue(hasattr(DataStore, 'created'))
        ds = DataStore()
        timestamp = time.time()
        val = {
            'timestamp': timestamp
        }
        ds._get_item = MagicMock(return_value=(val, None, None))
        result = ds.created('foo')
        self.assertEqual(timestamp, result)
        ds._get_item.assert_called_once_with('foo')

    def test_set_item(self):
        """
        Check the DataStore base class has a set_item method.
        """
        self.assertTrue(hasattr(DataStore, '_set_item'))
        ds = DataStore()
        self.assertRaises(NotImplementedError, ds._set_item, 'foo',
                          'some arbitrary yet meaningless value')

    def test_get_item(self):
        """
        Check the DataStore base class has a set_item method.
        """
        self.assertTrue(hasattr(DataStore, '_get_item'))
        ds = DataStore()
        self.assertRaises(NotImplementedError, ds._get_item, 'foo')

    def test__getitem__(self):
        """
        Check the DataStore base class gets the requested item and does the
        necessary magic to return the value without associated metadata.
        """
        self.assertTrue(hasattr(DataStore, '__getitem__'))
        ds = DataStore()
        val = 'some arbitrary yet meaningless value'
        ds._get_item = MagicMock(return_value=(val, None, None))
        result = ds['foo']
        self.assertEqual(val, result)
        ds._get_item.assert_called_once_with('foo')

    def test__setitem__(self):
        """
        Check the DataStore base class has a __setitem__ method.
        """
        self.assertTrue(hasattr(DataStore, '__setitem__'))
        ds = DataStore()
        val = 'some arbitrary yet meaningless value'
        ds._set_item = MagicMock()
        ds['foo'] = val
        self.assertEqual(1, ds._set_item.call_count)
        call_args = ds._set_item.call_args[0]
        self.assertEqual('foo', call_args[0])
        self.assertIsInstance(call_args[1], tuple)
        self.assertEqual(val, call_args[1][0])
        self.assertIsInstance(call_args[1][1], float)

    def test__iter__(self):
        """
        Check the DataStore base class has a __iter__ method.
        """
        self.assertTrue(hasattr(DataStore, '__delitem__'))
        ds = DataStore()
        with self.assertRaises(NotImplementedError):
            for k in iter(ds):
                pass

    def test__len__(self):
        """
        Check the DataStore base class has a __len__ method.
        """
        self.assertTrue(hasattr(DataStore, '__delitem__'))
        ds = DataStore()
        with self.assertRaises(NotImplementedError):
            len(ds)

    def test__del__(self):
        """
        Check the DataStore base class has a __delitem__ method.
        """
        self.assertTrue(hasattr(DataStore, '__delitem__'))
        ds = DataStore()
        with self.assertRaises(NotImplementedError):
            del ds['item']


class TestDictDataStore(unittest.TestCase):
    """
    Ensures that the in-memory Python dict based data store works as expected.
    """

    def setUp(self):
        """
        An item to play with.
        """
        self.item = {
            'foo': 'bar',
            'baz': [1, 2, 3]
        }

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
        self.assertEqual(0, len(store.keys()))
        store['foo'] = self.item
        self.assertTrue('foo' in store.keys())

    def test_set_item(self):
        """
        Ensures that the set_item method works as expected.
        """
        store = DictDataStore()
        store._set_item('foo', (self.item, time.time()))
        self.assertEqual(1, len(store.keys()))
        self.assertIn('foo', store.keys())
        self.assertEqual(self.item, store['foo'])

    def test__getitem__(self):
        """
        Ensures that the __getitem__ method works as expected.
        """
        store = DictDataStore()
        store._set_item('foo', (self.item, time.time()))
        self.assertEqual(self.item, store['foo'])

    def test__iter__(self):
        """
        Ensure that the __iter__ method works as expected.
        """
        store = DictDataStore()
        store._set_item('foo', (self.item, time.time()))
        items = [i for i in iter(store)]
        self.assertEqual(1, len(items))

    def test__len__(self):
        """
        Ensure that the __len__ method works as expected.
        """
        store = DictDataStore()
        store._set_item('foo', (self.item, time.time()))
        self.assertEqual(1, len(store))

    def test__delitem__(self):
        """
        Ensures that the __delitem__ method works as expected.
        """
        store = DictDataStore()
        store._set_item('foo', (self.item, time.time()))
        self.assertEqual(1, len(store.keys()))
        del store['foo']
        self.assertEqual(0, len(store.keys()))
