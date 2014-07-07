# -*- coding: utf-8 -*-
"""
A set of sanity checks to ensure that the messages are defined as expected.

Why..?

I want to create a fly in the ointment so that if changes are made to the
messages then it's impossible to miss (and inadvertently mess up). Not so
much TDD as a reminder to my future self (and other maintainers).

;-)
"""
from drogulus.dht.messages import (Error, Ping, Pong, Store, FindNode, Nodes,
                                   FindValue, Value, to_dict, from_dict,
                                   make_message)
from drogulus.dht.crypto import get_signed_item, construct_key
from drogulus.version import get_version
from hashlib import sha512
from .keys import PRIVATE_KEY, PUBLIC_KEY
import unittest
from uuid import uuid4


class TestMessages(unittest.TestCase):
    """
    Ensures the message classes are *defined* as expected and the relevant
    fields can be indexed.
    """

    def setUp(self):
        self.uuid = str(uuid4())
        self.node = PUBLIC_KEY
        self.sender = PUBLIC_KEY
        self.recipient = PUBLIC_KEY
        self.reply_port = 1908
        self.key = sha512(uuid4().bytes).hexdigest()
        self.version = get_version()
        self.seal = 'afakesealthatwillnotwork'

    def test_error(self):
        """
        Expected behaviour of an error message.
        """
        error = Error(self.uuid, self.recipient, self.sender, self.reply_port,
                      self.version, self.seal, 'ErrorType', {'foo': 'bar'})
        self.assertEqual(self.uuid, error.uuid)
        self.assertEqual(self.recipient, error.recipient)
        self.assertEqual(self.sender, error.sender)
        self.assertEqual(self.reply_port, error.reply_port)
        self.assertEqual(self.version, error.version)
        self.assertEqual(self.seal, error.seal)
        self.assertEqual('ErrorType', error.error)
        self.assertEqual({'foo': 'bar'}, error.details)

    def test_ping(self):
        """
        Expected behaviour of a ping message.
        """
        ping = Ping(self.uuid, self.recipient, self.sender, self.reply_port,
                    self.version, self.seal)
        self.assertEqual(self.uuid, ping.uuid)
        self.assertEqual(self.recipient, ping.recipient)
        self.assertEqual(self.sender, ping.sender)
        self.assertEqual(self.reply_port, ping.reply_port)
        self.assertEqual(self.version, ping.version)
        self.assertEqual(self.seal, ping.seal)

    def test_pong(self):
        """
        Expected behaviour of a pong message.
        """
        pong = Pong(self.uuid, self.recipient, self.sender, self.reply_port,
                    self.version, self.seal)
        self.assertEqual(self.uuid, pong.uuid)
        self.assertEqual(self.recipient, pong.recipient)
        self.assertEqual(self.sender, pong.sender)
        self.assertEqual(self.reply_port, pong.reply_port)
        self.assertEqual(self.version, pong.version)
        self.assertEqual(self.seal, pong.seal)

    def test_store(self):
        """
        Expected behaviour of a store message.
        """
        store = Store(self.uuid, self.recipient, self.sender, self.reply_port,
                      self.version, self.seal, self.key, 'value',
                      1350544046.084875, 0.0, self.version, PUBLIC_KEY,
                      'name', 'signature')
        self.assertEqual(self.uuid, store.uuid)
        self.assertEqual(self.recipient, store.recipient)
        self.assertEqual(self.sender, store.sender)
        self.assertEqual(self.reply_port, store.reply_port)
        self.assertEqual(self.version, store.version)
        self.assertEqual(self.seal, store.seal)
        self.assertEqual(self.key, store.key)
        self.assertEqual('value', store.value)
        self.assertEqual(1350544046.084875, store.timestamp)
        self.assertEqual(0.0, store.expires)
        self.assertEqual(self.version, store.created_with)
        self.assertEqual(PUBLIC_KEY, store.public_key)
        self.assertEqual('name', store.name)
        self.assertEqual('signature', store.signature)

    def test_find_node(self):
        """
        Expected behaviour of a findnode message.
        """
        fn = FindNode(self.uuid, self.recipient, self.sender, self.reply_port,
                      self.version, self.seal, self.key)
        self.assertEqual(self.uuid, fn.uuid)
        self.assertEqual(self.recipient, fn.recipient)
        self.assertEqual(self.sender, fn.sender)
        self.assertEqual(self.reply_port, fn.reply_port)
        self.assertEqual(self.version, fn.version)
        self.assertEqual(self.seal, fn.seal)
        self.assertEqual(self.key, fn.key)

    def test_nodes(self):
        """
        Expected behaviour of a nodes message.
        """
        nodes = Nodes(self.uuid, self.recipient, self.sender, self.reply_port,
                      self.version, self.seal,
                      ((self.node, '127.0.0.1', 1908, self.version)))
        self.assertEqual(self.uuid, nodes.uuid)
        self.assertEqual(self.recipient, nodes.recipient)
        self.assertEqual(self.sender, nodes.sender)
        self.assertEqual(self.reply_port, nodes.reply_port)
        self.assertEqual(self.version, nodes.version)
        self.assertEqual(self.seal, nodes.seal)
        self.assertEqual(((self.node, '127.0.0.1', 1908, self.version)),
                         nodes.nodes)

    def test_find_value(self):
        """
        Expected behaviour of a findvalue message.
        """
        fv = FindValue(self.uuid, self.recipient, self.sender, self.reply_port,
                       self.version, self.seal, self.key)
        self.assertEqual(self.uuid, fv.uuid)
        self.assertEqual(self.recipient, fv.recipient)
        self.assertEqual(self.sender, fv.sender)
        self.assertEqual(self.reply_port, fv.reply_port)
        self.assertEqual(self.version, fv.version)
        self.assertEqual(self.seal, fv.seal)
        self.assertEqual(self.key, fv.key)

    def test_value(self):
        """
        Expected behaviour of a value message.
        """
        val = Value(self.uuid, self.recipient, self.sender, self.reply_port,
                    self.version, self.seal, self.key, 'value',
                    1350544046.084875, 0.0, self.version, PUBLIC_KEY, 'name',
                    'signature')
        self.assertEqual(self.uuid, val.uuid)
        self.assertEqual(self.recipient, val.recipient)
        self.assertEqual(self.sender, val.sender)
        self.assertEqual(self.reply_port, val.reply_port)
        self.assertEqual(self.version, val.version)
        self.assertEqual(self.seal, val.seal)
        self.assertEqual(self.key, val.key)
        self.assertEqual('value', val.value)
        self.assertEqual(1350544046.084875, val.timestamp)
        self.assertEqual(0.0, val.expires)
        self.assertEqual(self.version, val.created_with)
        self.assertEqual(PUBLIC_KEY, val.public_key)
        self.assertEqual('name', val.name)
        self.assertEqual('signature', val.signature)


class TestDictConversion(unittest.TestCase):
    """
    Ensures functions for encoding and decoding messages in to and from
    dict objects to message based objects work as expected.
    """

    def setUp(self):
        """
        Gives us some messages to play with.
        """
        self.uuid = str(uuid4())
        self.node = PUBLIC_KEY
        self.recipient = PUBLIC_KEY
        self.sender = PUBLIC_KEY
        self.reply_port = 1908
        self.value = 1.234
        self.public_key = PUBLIC_KEY
        self.name = 'a_human_readable_key_name'
        self.key = construct_key(self.public_key, self.name)
        signed_dict = get_signed_item(self.key, self.value, self.public_key,
                                      PRIVATE_KEY, 1000)
        self.version = get_version()
        self.timestamp = signed_dict['timestamp']
        self.expires = signed_dict['expires']
        self.created_with = signed_dict['created_with']
        self.signature = signed_dict['signature']
        self.message = 'value'
        self.seal = 'afakesealthatwillnotwork'
        self.nodes = ((self.node, self.version, 'http://192.168.0.1:8080/'),)
        self.mock_message = Value(self.uuid, self.node, self.node,
                                  self.reply_port, self.version, self.seal,
                                  self.key, self.value, self.timestamp,
                                  self.expires, self.created_with,
                                  self.public_key, self.name, self.signature)

    def test_to_dict(self):
        """
        Simple good case.
        """
        result = to_dict(self.mock_message)
        self.assertIsInstance(result, dict)
        for k in ['uuid', 'recipient', 'sender', 'reply_port', 'version',
                  'seal', 'key', 'value', 'timestamp',
                  'expires', 'created_with', 'public_key', 'name',
                  'signature', 'message']:
            self.assertIn(k, result.keys())
            self.assertEqual(result[k], getattr(self, k))

    def test_from_dict_error(self):
        """
        Ensures a valid error message is correctly parsed.
        """
        mock_message = {
            'message': 'error',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal,
            'error': 'AnError',
            'details': {'key': 'value'},
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, Error)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.error, 'AnError')
        self.assertEqual(result.details, {'key': 'value'})

    def test_from_dict_ping(self):
        """
        Ensures a valid ping message is correctly parsed.
        """
        mock_message = {
            'message': 'ping',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, Ping)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)

    def test_from_dict_pong(self):
        """
        Ensures a valid pong message is correctly parsed.
        """
        mock_message = {
            'message': 'pong',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, Pong)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)

    def test_from_dict_store(self):
        """
        Ensures a valid store message is correctly parsed.
        """
        mock_message = {
            'message': 'store',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal,
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp,
            'expires': self.expires,
            'created_with': self.created_with,
            'public_key': self.public_key,
            'name': self.name,
            'signature': self.signature,
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, Store)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.value, self.value)
        self.assertEqual(result.timestamp, self.timestamp)
        self.assertEqual(result.expires, self.expires)
        self.assertEqual(result.created_with, self.created_with)
        self.assertEqual(result.public_key, self.public_key)
        self.assertEqual(result.name, self.name)
        self.assertEqual(result.signature, self.signature)

    def test_from_dict_findnode(self):
        """
        Ensures a valid findnode message is correctly parsed.
        """
        mock_message = {
            'message': 'findnode',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal,
            'key': self.key
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, FindNode)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.key, self.key)

    def test_from_dict_nodes(self):
        """
        Ensures a valid nodes message is correctly parsed.
        """
        mock_message = {
            'message': 'nodes',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal,
            'nodes': self.nodes
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, Nodes)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.nodes, self.nodes)

    def test_from_dict_findvalue(self):
        """
        Ensures a valid findvalue message is correctly parsed.
        """
        mock_message = {
            'message': 'findvalue',
            'uuid': self.uuid,
            'recipient': self.node,
            'sender': self.node,
            'reply_port': self.reply_port,
            'version': self.version,
            'seal': self.seal,
            'key': self.key
        }
        result = from_dict(mock_message)
        self.assertIsInstance(result, FindValue)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.key, self.key)

    def test_from_dict_value(self):
        """
        Ensures a valid value message is correctly parsed.
        """
        mock_message = to_dict(self.mock_message)
        result = from_dict(mock_message)
        self.assertIsInstance(result, Value)
        self.assertEqual(result.uuid, self.uuid)
        self.assertEqual(result.recipient, self.node)
        self.assertEqual(result.sender, self.node)
        self.assertEqual(result.reply_port, self.reply_port)
        self.assertEqual(result.version, self.version)
        self.assertEqual(result.seal, self.seal)
        self.assertEqual(result.key, self.key)
        self.assertEqual(result.value, self.value)
        self.assertEqual(result.timestamp, self.timestamp)
        self.assertEqual(result.expires, self.expires)
        self.assertEqual(result.created_with, self.created_with)
        self.assertEqual(result.public_key, self.public_key)
        self.assertEqual(result.name, self.name)
        self.assertEqual(result.signature, self.signature)

    def test_from_dict_unknown_request(self):
        """
        Ensures the correct exception is raised if the message is not
        recognised.
        """
        # "pang" is "bang" in Swedish (apparently).
        mock_message = {
            'message': 'pang',
            'uuid': self.uuid,
            'node': self.node,
            'version': self.version
        }
        with self.assertRaises(ValueError) as cm:
            from_dict(mock_message)
        ex = cm.exception
        self.assertEqual('pang is not a valid message type.', ex.args[0])


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
        node = PUBLIC_KEY
        reply_port = 1908
        version = get_version()
        result = make_message(Ping, {'uuid': uuid, 'recipient': node,
                                     'sender': node, 'reply_port': reply_port,
                                     'version': version, 'seal': 'fakeseal'})
        self.assertIsInstance(result, Ping)
        self.assertEqual(uuid, result.uuid)
        self.assertEqual(node, result.recipient)
        self.assertEqual(node, result.sender)
        self.assertEqual(reply_port, result.reply_port)
        self.assertEqual(version, result.version)
        self.assertEqual('fakeseal', result.seal)

    def test_make_message_bad_values(self):
        """
        The values to be used to instantiate the class should be valid. If not
        the correct exception is raised.
        """
        with self.assertRaises(ValueError) as cm:
            make_message(Ping, {'uuid': 1, 'recipient': 2, 'sender': 3,
                                'reply_port': '1908', 'version': 4,
                                'seal': 5})
        ex = cm.exception
        details = ex.args[0]
        self.assertEqual(6, len(details))
        self.assertEqual('Invalid value.', details['uuid'])
        self.assertEqual('Invalid value.', details['recipient'])
        self.assertEqual('Invalid value.', details['sender'])
        self.assertEqual('Invalid value.', details['reply_port'])
        self.assertEqual('Invalid value.', details['version'])
        self.assertEqual('Invalid value.', details['seal'])

    def test_make_message_missing_fields(self):
        """
        The correct fields must all exist in the provided data dictionary.
        """
        with self.assertRaises(ValueError) as cm:
            make_message(Ping, {'foo': 1, 'bar': 2})
        ex = cm.exception
        details = ex.args[0]
        self.assertEqual(6, len(details))
        self.assertEqual('Missing field.', details['uuid'])
        self.assertEqual('Missing field.', details['recipient'])
        self.assertEqual('Missing field.', details['sender'])
        self.assertEqual('Missing field.', details['reply_port'])
        self.assertEqual('Missing field.', details['version'])
        self.assertEqual('Missing field.', details['seal'])
