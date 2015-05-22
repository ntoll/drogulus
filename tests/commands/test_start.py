# -*- coding: utf-8 -*-
"""
Ensures the Start class works as expected.
"""
import unittest
import os.path
from drogulus.commands.start import Start
from drogulus.net.http import HttpConnector
from unittest import mock
from ..keys import PRIVATE_KEY, PUBLIC_KEY


class TestStart(unittest.TestCase):
    """
    Exercises the Start class (a child of cliff.command.Command).
    """

    def test_get_description(self):
        """
        Calling the get_description method should return a non-empty string.
        """
        start = Start(None, None)
        result = start.get_description()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_get_parser(self):
        """
        Ensure the expected argument specifications are created in the
        resulting parser object.
        """
        start = Start(None, None)
        parser = start.get_parser('test')
        # passphrase
        self.assertEqual('passphrase', parser._actions[1].dest)
        self.assertEqual(str, parser._actions[1].type)
        self.assertEqual('', parser._actions[1].default)
        self.assertEqual('?', parser._actions[1].nargs)
        # keys
        self.assertEqual('keys', parser._actions[2].dest)
        self.assertEqual(str, parser._actions[2].type)
        self.assertEqual('', parser._actions[2].default)
        self.assertEqual('?', parser._actions[2].nargs)
        # peers
        self.assertEqual('peers', parser._actions[3].dest)
        self.assertEqual(str, parser._actions[3].type)
        self.assertEqual('', parser._actions[3].default)
        self.assertEqual('?', parser._actions[3].nargs)
        # port
        self.assertEqual('port', parser._actions[4].dest)
        self.assertEqual(int, parser._actions[4].type)
        self.assertEqual(1908, parser._actions[4].default)
        self.assertEqual('?', parser._actions[4].nargs)
        # whoami
        self.assertEqual('whoami', parser._actions[5].dest)
        self.assertEqual(str, parser._actions[5].type)
        self.assertEqual('', parser._actions[5].default)
        self.assertEqual('?', parser._actions[5].nargs)

    def test_take_action(self):
        """
        Check, given a good case, the appropriate calls are made to start a
        local node. Should this be tested? Probably not, but since this is how
        a node is likely to be started I'd like to exercise it just so that if
        it ever gets changed then a test is likely to fail - meaning such a
        fundamental step is *carefully* updated in future and default settings
        cannot be changed by mistake.

        This code is a bit FUBAR (see PEP8 related indent fun). ;-)
        """
        passphrase = 'passphrase'
        whoami = 'whoami.json'
        alias = 'alias.json'
        key_dir = 'key_dir'
        port = 1908
        peers = None
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = passphrase
        parsed_args.port = port
        parsed_args.keys = key_dir
        parsed_args.whoami = whoami
        parsed_args.alias = alias
        parsed_args.peers = peers

        # patch logging
        with mock.patch('drogulus.commands.start.logging.getLogger',
                        return_value=mock.MagicMock()) as patched_log:
            # patch RSA
            with mock.patch('drogulus.commands.start.get_keys',
                            return_value=(PRIVATE_KEY,
                                          PUBLIC_KEY)) as patched_rsa:
                # patch whoami
                with mock.patch('drogulus.commands.start.get_whoami',
                                return_value={}) as patched_whoami:
                    # patch asyncio
                    loop = mock.MagicMock()
                    loop.create_server = mock.MagicMock()
                    loop.create_server.return_value = mock.MagicMock()
                    loop.run_until_complete = mock.MagicMock()
                    loop.run_until_complete.return_value = mock.MagicMock()
                    loop.run_forever = mock.MagicMock()

                    def side_effect():
                        raise KeyboardInterrupt()
                    loop.run_forever.side_effect = side_effect
                    with mock.patch('drogulus.commands.start.' +
                                    'asyncio.get_event_loop',
                                    return_value=loop) as patched_asyncio:
                        # Patch Drogulus class
                        drog = mock.MagicMock()
                        drog._node = mock.MagicMock()
                        drog._node.routing_table = mock.MagicMock()
                        drog._node.routing_table.dump = mock.MagicMock()
                        drog._node.routing_table.dump.return_value = {}
                        with mock.patch('drogulus.commands.start.Drogulus',
                                        return_value=drog) as\
                                patched_drogulus:
                            start = Start(None, None)
                            start.take_action(parsed_args)
                            self.assertTrue(patched_log.call_count > 0)
                            priv_path = os.path.join(key_dir,
                                                     'drogulus.scrypt')
                            pub_path = os.path.join(key_dir,
                                                    'drogulus.pub')
                            patched_rsa.assert_called_once_with(passphrase,
                                                                priv_path,
                                                                pub_path)
                            patched_whoami.assert_called_once_with(whoami)
                            self.assertEqual(2,
                                             patched_asyncio.call_count)
                            self.assertEqual(1,
                                             patched_drogulus.call_count)
                            called_with = patched_drogulus.call_args[0]
                            self.assertEqual(called_with[0], PRIVATE_KEY)
                            self.assertEqual(called_with[1], PUBLIC_KEY)
                            self.assertEqual(called_with[2], loop)
                            self.assertIsInstance(called_with[3],
                                                  HttpConnector)
                            self.assertEqual(called_with[4], port)
                            self.assertEqual(called_with[5], {})
                            cc = drog._node.routing_table.dump.call_count
                            self.assertEqual(1, cc)

    def test_take_action_no_passphrase(self):
        """
        If no passphrase argument is supplied ensure that the script prompts
        for one and continues with the entered value.
        """
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = None
        parsed_args.keys = None
        start = Start(None, None)
        with mock.patch('drogulus.commands.start.getpass',
                        return_value='  foo  ') as patched_getpass:

            def side_effect(*args):
                raise Exception('Boom!')
            with mock.patch('drogulus.commands.start.get_keys',
                            side_effect=side_effect) as patched_get_keys:
                with self.assertRaises(Exception):
                    start.take_action(parsed_args)
                self.assertEqual(1, patched_getpass.call_count)
                patched_get_keys.assert_called_once_with('foo', None, None)

    def test_take_action_no_passphrase_entered(self):
        """
        If no passphrase argument is supplied and no passphrase entered when
        prompted ensure a ValueError is raised.
        """
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = None
        start = Start(None, None)
        with mock.patch('drogulus.commands.start.getpass', return_value=''):
            with self.assertRaises(ValueError) as raised:
                start.take_action(parsed_args)
                self.assertEqual(raised.exception.args[0],
                                 'You must supply a passphrase.')

    def test_take_action_bad_keys(self):
        """
        Given a passphrase value, if the get_keys function fails ensure this
        is logged and the exception is raised to the caller.
        """
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = 'foo'
        start = Start(None, None)

        def side_effect(*args):
            raise ValueError('Boom!')

        with mock.patch('drogulus.commands.start.logging.getLogger',
                        return_value=mock.MagicMock()) as patched_log:
            with mock.patch('drogulus.commands.start.get_keys',
                            side_effect=side_effect) as patched_get_keys:
                    with self.assertRaises(ValueError) as raised:
                        start.take_action(parsed_args)
                        self.assertEqual(1, patched_get_keys.call_count)
                        self.assertEqual(2, patched_log.call_count)
                        self.assertEqual(raised.exception.args[0], 'Boom!')

    def test_take_action_no_whoami(self):
        """
        If no valid whoami file is specified ensure this is logged and the
        whoami value is set to None.
        """
        passphrase = 'passphrase'
        whoami = 'whoami.json'
        alias = 'alias.json'
        key_dir = 'key_dir'
        port = 1908
        peers = None
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = passphrase
        parsed_args.port = port
        parsed_args.keys = key_dir
        parsed_args.whoami = whoami
        parsed_args.alias = alias
        parsed_args.peers = peers

        # patch logging
        with mock.patch('drogulus.commands.start.logging.getLogger',
                        return_value=mock.MagicMock()):
            # patch RSA
            with mock.patch('drogulus.commands.start.get_keys',
                            return_value=(PRIVATE_KEY,
                                          PUBLIC_KEY)):

                def run_whoami(*args):
                    raise ValueError('Bang!')
                # patch whoami
                with mock.patch('drogulus.commands.start.get_whoami',
                                side_effect=run_whoami):
                    # patch asyncio
                    loop = mock.MagicMock()
                    loop.create_server = mock.MagicMock()
                    loop.create_server.return_value = mock.MagicMock()
                    loop.run_until_complete = mock.MagicMock()
                    loop.run_until_complete.return_value = mock.MagicMock()
                    loop.run_forever = mock.MagicMock()

                    def side_effect():
                        raise KeyboardInterrupt()
                    loop.run_forever.side_effect = side_effect
                    with mock.patch('drogulus.commands.start.' +
                                    'asyncio.get_event_loop',
                                    return_value=loop):
                        # Patch Drogulus class
                        drog = mock.MagicMock()
                        drog._node = mock.MagicMock()
                        drog._node.routing_table = mock.MagicMock()
                        drog._node.routing_table.dump = mock.MagicMock()
                        drog._node.routing_table.dump.return_value = {}
                        with mock.patch('drogulus.commands.start.Drogulus',
                                        return_value=drog) as\
                                patched_drogulus:
                            start = Start(None, None)
                            start.take_action(parsed_args)
                            self.assertEqual(1,
                                             patched_drogulus.call_count)
                            called_with = patched_drogulus.call_args[0]
                            self.assertEqual(called_with[5], None)

    def test_take_action_calls_make_http_handler(self):
        """
        Ensure that the make_http_handler function is called in order to set up
        the HTTP based API.
        """
        passphrase = 'passphrase'
        whoami = 'whoami.json'
        alias = 'alias.json'
        key_dir = 'key_dir'
        port = 1908
        peers = None
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = passphrase
        parsed_args.port = port
        parsed_args.keys = key_dir
        parsed_args.whoami = whoami
        parsed_args.alias = alias
        parsed_args.peers = peers

        # patch logging
        with mock.patch('drogulus.commands.start.logging.getLogger',
                        return_value=mock.MagicMock()):
            # patch RSA
            with mock.patch('drogulus.commands.start.get_keys',
                            return_value=(PRIVATE_KEY,
                                          PUBLIC_KEY)):
                # patch whoami
                with mock.patch('drogulus.commands.start.get_whoami',
                                return_value={}):
                    # patch asyncio
                    loop = mock.MagicMock()
                    loop.create_server = mock.MagicMock()
                    loop.create_server.return_value = mock.MagicMock()
                    loop.run_until_complete = mock.MagicMock()
                    loop.run_until_complete.return_value = mock.MagicMock()
                    loop.run_forever = mock.MagicMock()

                    def side_effect():
                        raise KeyboardInterrupt()
                    loop.run_forever.side_effect = side_effect
                    with mock.patch('drogulus.commands.start.' +
                                    'asyncio.get_event_loop',
                                    return_value=loop):
                        # Patch Drogulus class
                        drog = mock.MagicMock()
                        drog._node = mock.MagicMock()
                        drog._node.routing_table = mock.MagicMock()
                        drog._node.routing_table.dump = mock.MagicMock()
                        drog._node.routing_table.dump.return_value = {}
                        with mock.patch('drogulus.commands.start.Drogulus',
                                        return_value=drog):
                            with mock.patch('drogulus.commands.start.' +
                                            'make_http_handler') as fake_mhh:
                                start = Start(None, None)
                                start.take_action(parsed_args)
                                self.assertEqual(1,
                                                 loop.create_server.call_count)
                                self.assertEqual(1, fake_mhh.call_count)

    def test_take_action_has_peer_file_to_load(self):
        """
        If the path to a peer file (containing the peer-nodes backed up from
        an existing routing table) is specified ensure this is loaded and
        passed to the local node so its own routing table can be
        "reconstituted" from it.
        """
        passphrase = 'passphrase'
        whoami = 'whoami.json'
        alias = 'alias.json'
        key_dir = 'key_dir'
        port = 1908
        peers = 'peers.json'
        parsed_args = mock.MagicMock()
        parsed_args.passphrase = passphrase
        parsed_args.port = port
        parsed_args.keys = key_dir
        parsed_args.whoami = whoami
        parsed_args.alias = alias
        parsed_args.peers = peers

        # patch logging
        with mock.patch('drogulus.commands.start.logging.getLogger',
                        return_value=mock.MagicMock()):
            # patch RSA
            with mock.patch('drogulus.commands.start.get_keys',
                            return_value=(PRIVATE_KEY,
                                          PUBLIC_KEY)):

                def run_whoami(*args):
                    raise ValueError('Bang!')
                # patch whoami
                with mock.patch('drogulus.commands.start.get_whoami',
                                side_effect=run_whoami):
                    # patch asyncio
                    loop = mock.MagicMock()
                    loop.create_server = mock.MagicMock()
                    loop.create_server.return_value = mock.MagicMock()
                    loop.run_until_complete = mock.MagicMock()
                    loop.run_until_complete.return_value = mock.MagicMock()
                    loop.run_forever = mock.MagicMock()

                    def side_effect():
                        raise KeyboardInterrupt()
                    loop.run_forever.side_effect = side_effect
                    with mock.patch('drogulus.commands.start.' +
                                    'asyncio.get_event_loop',
                                    return_value=loop):
                        # Patch Drogulus class
                        drog = mock.MagicMock()
                        drog.join = mock.MagicMock()
                        drog._node = mock.MagicMock()
                        drog._node.routing_table = mock.MagicMock()
                        drog._node.routing_table.dump = mock.MagicMock()
                        drog._node.routing_table.dump.return_value = {}
                        with mock.patch('drogulus.commands.start.Drogulus',
                                        return_value=drog):
                            # Patch open
                            mr = mock.MagicMock()
                            mr = mock.MagicMock()
                            mr.read.return_value = '{}'
                            with mock.patch('builtins.open',
                                            return_value=mr):
                                start = Start(None, None)
                                start.take_action(parsed_args)
                                drog.join.assert_called_once_with({})
