# -*- coding: utf-8 -*-
"""
A set of sanity checks to ensure that functions concerning message validation
work correctly.
"""
from drogulus.dht.validators import (validate_timestamp, validate_port,
                                     validate_string, validate_dict,
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

    def test_validate_timestamp_wrong_value(self):
        """
        A timestamp must be a 0.0 or more positive number.
        """
        self.assertFalse(validate_timestamp(-1.234))
        self.assertTrue(validate_timestamp(0.0))

    def test_validate_port(self):
        """
        A port should be an integer within the correct range.
        """
        self.assertTrue(validate_port(1908))

    def test_validate_port_wrong_type(self):
        self.assertFalse(validate_port("1908"))

    def test_validate_port_too_low(self):
        self.assertFalse(validate_port(-1))
        self.assertTrue(validate_port(0))

    def test_validate_port_too_high(self):
        self.assertTrue(validate_port(49151))
        self.assertFalse(validate_port(49152))

    def test_validate_string_str(self):
        """
        Regular Python strings pass.
        """
        self.assertTrue(validate_string('hello'))

    def test_validate_string_wrong_type(self):
        """
        It fails if the value is not a string.
        """
        self.assertFalse(validate_string(1))

    def test_validate_dict(self):
        """
        A dictionary containing key/value strings passes.
        """
        self.assertTrue(validate_dict({'foo': 'bar'}))

    def test_validate_dict_wrong_type(self):
        """
        If the dict isn't a dictionary then fail.
        """
        self.assertFalse(validate_dict(('foo', 'bar')))

    def test_validate_node(self):
        """
        A tuple containing id and IP address strings, a port integer and
        version string passes.
        """
        self.assertTrue(validate_node(('id', '0.1',
                                      'http://192.168.0.1:9999/')))

    def test_validate_node_wrong_type(self):
        """
        The node should be expressed within a tuple.
        """
        self.assertFalse(validate_node(['id', '0.1',
                                      'http://192.168.0.1:9999/']))

    def test_validate_node_bad_id(self):
        """
        The node's id should be a string.
        """
        self.assertFalse(validate_node((123, '0.1',
                                      'http://192.168.0.1:9999/')))

    def test_validate_node_invalid_version(self):
        """
        The version number should be a string.
        """
        self.assertFalse(validate_node(('id', 0.1,
                                      'http://192.168.0.1:9999/')))

    def test_validate_node_bad_uri(self):
        """
        The URI should be a string.
        """
        self.assertFalse(validate_node(('id', '0.1',
                                       ['http://192.168.0.1:9999/'])))

    def test_validate_nodes(self):
        """
        A tuple of zero or more nodes is valid.
        """
        self.assertTrue(validate_nodes((('id', '0.1',
                                       'http://192.168.0.1:9999/'),)))

    def test_validate_nodes_wrong_type(self):
        """
        Nodes can only be expressed in tuples.
        """
        self.assertFalse(validate_nodes([('id', '0.1',
                                         'http://192.168.0.1:9999/'),]))

    def test_validate_nodes_bad_node(self):
        """
        A tuple of nodes is only valid is the nodes contained therein are also
        valid.
        """
        self.assertFalse(validate_nodes(((123, '0.1',
                                         'http://192.168.0.1:9999/'))))

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
        self.assertEqual(17, len(VALIDATORS))
        self.assertEqual(VALIDATORS['uuid'], validate_string)
        self.assertEqual(VALIDATORS['recipient'], validate_string)
        self.assertEqual(VALIDATORS['sender'], validate_string)
        self.assertEqual(VALIDATORS['version'], validate_string)
        self.assertEqual(VALIDATORS['seal'], validate_string)
        self.assertEqual(VALIDATORS['error'], validate_string)
        self.assertEqual(VALIDATORS['details'], validate_dict)
        self.assertEqual(VALIDATORS['key'], validate_string)
        self.assertEqual(VALIDATORS['value'], validate_value)
        self.assertEqual(VALIDATORS['timestamp'], validate_timestamp)
        self.assertEqual(VALIDATORS['expires'], validate_timestamp)
        self.assertEqual(VALIDATORS['created_with'], validate_string)
        self.assertEqual(VALIDATORS['public_key'], validate_string)
        self.assertEqual(VALIDATORS['name'], validate_string)
        self.assertEqual(VALIDATORS['signature'], validate_string)
        self.assertEqual(VALIDATORS['nodes'], validate_nodes)
        self.assertEqual(VALIDATORS['reply_port'], validate_port)
