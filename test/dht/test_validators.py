# -*- coding: utf-8 -*-
"""
A set of sanity checks to ensure that function concerning message validation
work correctly.
"""
from drogulus.dht.validators import (validate_timestamp, validate_code,
                                     validate_string, validate_meta,
                                     validate_node, validate_nodes,
                                     validate_value, VALIDATORS)
import unittest
import time


class TestValidators(unittest.TestCase):
    """
    Ensures the validator functions work as expected
    """

    def test_validate_timestamp(self):
        """
        The good case passes.
        """
        self.assertTrue(validate_timestamp(time.time()))

    def test_validate_timestamp_wrong_type(self):
        """
        Timestamps are floating point numbers.
        """
        self.assertFalse(validate_timestamp(123))

    def test_validate_code(self):
        """
        The good error code passes.
        """
        self.assertTrue(validate_code(1))

    def test_validate_code_unknown(self):
        """
        Using an unknown error code number fails.
        """
        self.assertFalse(validate_code(0))

    def test_validate_code_wrong_type(self):
        """
        Error codes are integers.
        """
        self.assertFalse(validate_code('1'))

    def test_validate_string_str(self):
        """
        Regular Python strings pass.
        """
        self.assertTrue(validate_string('hello'))

    def test_validate_string_unicode(self):
        """
        Unicode strings pass.
        """
        self.assertTrue(validate_string(u'hello'))

    def test_validate_string_wrong_type(self):
        """
        It fails if the value is not a string.
        """
        self.assertFalse(validate_string(1))

    def test_validate_meta(self):
        """
        A dictionary containing key/value strings passes.
        """
        self.assertTrue(validate_meta({'foo': 'bar'}))

    def test_validate_meta_wrong_type(self):
        """
        If the meta-data isn't a dictionary then fail.
        """
        self.assertFalse(validate_meta(('foo', 'bar')))

    def test_validate_meta_bad_key(self):
        """
        All keys must be strings.
        """
        self.assertFalse(validate_meta({1: 'foo'}))

    def test_validate_meta_bad_value(self):
        """
        All values must be strings.
        """
        self.assertFalse(validate_meta({'foo': 1}))

    def test_validate_node(self):
        """
        A tuple containing an IP address string and port integer passes.
        """
        self.assertTrue(validate_node(('id', '127.0.0.1', 1908, '0.1')))

    def test_validate_node_wrong_type(self):
        """
        The node should be expressed within a tuple.
        """
        self.assertFalse(validate_node(['id', '127.0.0.1', 1908, '0.1']))

    def test_validate_node_bad_id(self):
        """
        The node's id should be a string.
        """
        self.assertFalse(validate_node((123, '127.0.0.1', 1908, '0.1')))

    def test_validate_node_bad_ip_address(self):
        """
        The IP address should be a string.
        """
        self.assertFalse(validate_node(('id', [127, 0, 0, 1], 1908, '0.1')))

    def test_validate_node_bad_port(self):
        """
        The port should be an integer.
        """
        self.assertFalse(validate_node(('id', '127.0.0.1', '1908', '0.1')))

    def test_validate_node_invalid_port_too_low(self):
        """
        The port should be a positive integer
        """
        self.assertTrue(validate_node(('id', '127.0.0.1', 0, '0.1')))
        self.assertFalse(validate_node(('id', '127.0.0.1', -1, '0.1')))

    def test_validate_node_invalid_port_too_high(self):
        """
        The port should be <= 49151.
        """
        self.assertTrue(validate_node(('id', '127.0.0.1', 49151, '0.1')))
        self.assertFalse(validate_node(('id', '127.0.0.1', 49152, '0.1')))

    def test_validate_node_invalid_version(self):
        """
        The if should be a string.
        """
        self.assertFalse(validate_node(('id', '127.0.0.1', 1908, 0.1)))

    def test_validate_nodes(self):
        """
        A tuple of zero or more nodes is valid.
        """
        self.assertTrue(validate_nodes((('id', '127.0.0.1', 1908, '0.1'),)))

    def test_validate_nodes_wrong_type(self):
        """
        Nodes can only be expressed in tuples.
        """
        self.assertFalse(validate_nodes([('id', '127.0.0.1', 1908, '0.1')]))

    def test_validate_nodes_bad_node(self):
        """
        A tuple of nodes is only valid is the nodes contained therein are also
        valid.
        """
        self.assertFalse(validate_nodes(((123, [127, 0, 0, 1], 1908, '0.1'))))

    def test_validate_value(self):
        """
        Checks the validity of values stored in the DHT. Currently always
        returns True but in the future may place limits on value sizes.
        """
        self.assertTrue(validate_value('foo'))

    def test_validate_VALIDATORS(self):
        """
        Ensures that the VALIDATORS dict maps the field names to validator
        functions correctly.
        """
        self.assertEqual(15, len(VALIDATORS))
        self.assertEqual(VALIDATORS['uuid'], validate_string)
        self.assertEqual(VALIDATORS['node'], validate_string)
        self.assertEqual(VALIDATORS['code'], validate_code)
        self.assertEqual(VALIDATORS['title'], validate_string)
        self.assertEqual(VALIDATORS['details'], validate_meta)
        self.assertEqual(VALIDATORS['version'], validate_string)
        self.assertEqual(VALIDATORS['key'], validate_string)
        self.assertEqual(VALIDATORS['value'], validate_value)
        self.assertEqual(VALIDATORS['timestamp'], validate_timestamp)
        self.assertEqual(VALIDATORS['expires'], validate_timestamp)
        self.assertEqual(VALIDATORS['public_key'], validate_string)
        self.assertEqual(VALIDATORS['name'], validate_string)
        self.assertEqual(VALIDATORS['meta'], validate_meta)
        self.assertEqual(VALIDATORS['sig'], validate_string)
        self.assertEqual(VALIDATORS['nodes'], validate_nodes)
