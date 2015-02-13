# -*- coding: utf-8 -*-
"""
Ensures the KeyGen class works as expected.
"""
import unittest
import os
import os.path
from drogulus.commands.keygen import KeyGen
from drogulus.commands.utils import APPNAME, data_dir
from unittest import mock


class TestKeyGen(unittest.TestCase):
    """
    Exercises the KeyGen class (a child of cliff.command.Command) to ensure
    it works in the expected manner.
    """

    def test_get_description(self):
        """
        Calling the get_description method should return a non-empty string.
        """
        keygen = KeyGen(None, None)
        result = keygen.get_description()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_get_parser(self):
        """
        Ensure the "size" argument specification is created in the resulting
        parser object.
        """
        keygen = KeyGen(None, None)
        parser = keygen.get_parser('test')
        self.assertEqual('size', parser._actions[1].dest)

    def test_take_action_good_pasphrase(self):
        """
        Ensure the take_action method processes the arguments and good user
        input correctly: an rsa keypair is created, output files specified and
        the utils.save_keys method is called.
        """
        with mock.patch('getpass.getpass', return_value='passphrase'):
            keygen = KeyGen(None, None)
            with mock.patch('drogulus.commands.keygen.save_keys') as sk:
                parsed_args = mock.MagicMock()
                parsed_args.size = 512
                mock_pub = mock.MagicMock()
                mock_pub.save_pkcs1 = mock.MagicMock(return_value=b'pub')
                mock_priv = mock.MagicMock()
                mock_priv.save_pkcs1 = mock.MagicMock(return_value=b'priv')
                return_val = (mock_pub, mock_priv)
                with mock.patch('rsa.newkeys',
                                return_value=return_val) as mock_newkeys:
                    keygen.take_action(parsed_args)
                    self.assertEqual(1, mock_newkeys.call_count)
                    self.assertEqual(1, sk.call_count)
                    output_pub = os.path.join(data_dir(),
                                              '{}.pub'.format(APPNAME))
                    output_priv = os.path.join(data_dir(),
                                               '{}.scrypt'.format(APPNAME))
                    self.assertEqual(sk.call_args[0][0], 'priv')
                    self.assertEqual(sk.call_args[0][1], 'pub')
                    self.assertEqual(sk.call_args[0][2], 'passphrase')
                    self.assertEqual(sk.call_args[0][3], output_priv)
                    self.assertEqual(sk.call_args[0][4], output_pub)

    def test_take_action_passphrase_mismatch(self):
        """
        If the requested passphrase doesn't match its confirmation then
        complain.
        """
        with mock.patch('getpass.getpass', side_effect=['good', 'bad']):
            keygen = KeyGen(None, None)
            parsed_args = mock.MagicMock()
            parsed_args.size = 512
            with self.assertRaises(ValueError) as ex:
                keygen.take_action(parsed_args)
            self.assertEqual('Passphrase and confirmation did not match.',
                             ex.exception.args[0])
