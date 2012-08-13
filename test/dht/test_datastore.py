"""
Ensures datastore related classes work as expected.
"""
from drogulus.dht.datastore import DataStore, DictDataStore
import unittest


class TestDataStore(unittest.TestCase):
    """
    Ensures the base class is defined as expected (no functionality is built
    in to the class). Basically, a bunch of trivial sanity tests.
    """

    def testKeys(self):
        """
        Check the DataStore base class has a keys method.
        """
        self.assertTrue(hasattr(DataStore, 'keys'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.keys())

    def testLastPublished(self):
        """
        Check the DataStore base class has a lastPublished method.
        """
        self.assertTrue(hasattr(DataStore, 'lastPublished'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.lastPublished(123))

    def testOriginalPublisher(self):
        """
        Check the DataStore base class has an originalPublisherID method.
        """
        self.assertTrue(hasattr(DataStore, 'originalPublisherID'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.originalPublisherID(123))

    def testSetItem(self):
        """
        Check the DataStore base class has an originalPublisher method.
        """
        self.assertTrue(hasattr(DataStore, 'setItem'))
        ds = DataStore()
        self.assertEqual(NotImplemented, ds.setItem(123, 'value', 1, 2, 3))

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

    def test__init__(self):
        """
        Ensures the DictDataStore is instantiated to an expected state.
        """
        store = DictDataStore()
        self.assertTrue(hasattr(store, '_dict'))
        self.assertEqual({}, store._dict)

    def testKeys(self):
        """
        Ensure the keys method works as expected.
        """
        store = DictDataStore()
        self.assertEqual([], store.keys())
        store['foo'] = ('bar', 1, 2, 3)
        self.assertTrue('foo' in store.keys())

    def testLastPublished(self):
        """
        Ensures the correct value is returned from lastPublished for a given
        key.
        """
        store = DictDataStore()
        store['foo'] = ('bar', 1, 2, 3)
        self.assertEqual(1, store.lastPublished('foo'))

    def testOriginalPublisherID(self):
        """
        Ensures the correct value is returned from originalPublisherID for a
        given key.
        """
        store = DictDataStore()
        store['foo'] = ('bar', 1, 2, 3)
        self.assertEqual(3, store.originalPublisherID('foo'))

    def testOriginalPublishTime(self):
        """
        Ensures the correct value is returned from originalPublishTime for a
        given key.
        """
        store = DictDataStore()
        store['foo'] = ('bar', 1, 2, 3)
        self.assertEqual(2, store.originalPublishTime('foo'))

    def testSetItem(self):
        """
        Ensures that the setItem method works as expected.
        """
        store = DictDataStore()
        store.setItem('foo', 'bar', 1, 2, 3)
        self.assertEqual(1, len(store.keys()))
        self.assertEqual('foo', store.keys()[0])
        self.assertEqual('bar', store['foo'])

    def test__getitem__(self):
        """
        Ensures that the __getitem__ method works as expected.
        """
        store = DictDataStore()
        store.setItem('foo', 'bar', 1, 2, 3)
        self.assertEqual('bar', store['foo'])

    def test__delitem__(self):
        """
        Ensures that the __delitem__ method works as expected.
        """
        store = DictDataStore()
        store.setItem('foo', 'bar', 1, 2, 3)
        self.assertEqual(1, len(store.keys()))
        del store['foo']
        self.assertEqual(0, len(store.keys()))
