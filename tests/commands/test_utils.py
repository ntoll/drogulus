# -*- coding: utf-8 -*-
"""
Ensures the functions found in the utils module work as expected.
"""
import unittest
import tempfile
import uuid
import rsa
import os
import os.path
from drogulus.commands.utils import (APPNAME, APPAUTHOR, data_dir, log_dir,
                                     get_keys, save_keys, get_whoami)
from unittest import mock


class TestUtils(unittest.TestCase):
    """
    Ensures utility functions and module attributes work as expected.
    """

    def test_APPNAME(self):
        """
        The APPNAME constant should be a string.
        """
        self.assertIsInstance(APPNAME, str)

    def test_APPAUTHOR(self):
        """
        The APPAUTHOR constant should be a string.
        """
        self.assertIsInstance(APPAUTHOR, str)

    def test_data_dir(self):
        """
        Ensure the function returns a string representation of a an existing
        directory on the filesystem.
        """
        random_dir = str(uuid.uuid4())
        tmp = os.path.join(tempfile.gettempdir(), random_dir)
        with mock.patch('drogulus.commands.utils.user_data_dir',
                        return_value=tmp):
            result = data_dir()
            self.assertIsInstance(result, str)
            self.assertTrue(os.path.exists(result))

    def test_log_dir(self):
        """
        Ensure the function returns a string representation of an existing
        directory on the filesystem.
        """
        random_dir = str(uuid.uuid4())
        tmp = os.path.join(tempfile.gettempdir(), random_dir)
        with mock.patch('drogulus.commands.utils.user_log_dir',
                        return_value=tmp):
            result = log_dir()
            self.assertIsInstance(result, str)
            self.assertTrue(os.path.exists(result))

    def test_get_keys_good_keys(self):
        """
        Ensures that good keys are recovered from the default locations in
        the filesystem. The keys are byte representations of pkcs1.
        """
        tmp = tempfile.gettempdir()
        passphrase = 'foobarbaz'
        with mock.patch('drogulus.commands.utils.data_dir',
                        return_value=tmp):
            # create and save something to test
            (pub, priv) = rsa.newkeys(512)
            private_key = priv.save_pkcs1()
            public_key = pub.save_pkcs1()
            out_priv = os.path.join(tmp, '{}.scrypt'.format(APPNAME))
            out_pub = os.path.join(tmp, '{}.pub'.format(APPNAME))
            save_keys(private_key, public_key, passphrase, out_priv, out_pub)
            actual_private, actual_public = get_keys(passphrase)
            self.assertEqual(private_key, actual_private)
            self.assertEqual(public_key, actual_public)

    def test_get_keys_bad_passphrase(self):
        """
        Ensures that an invalid passphrase results in a ValueError.
        """
        tmp = tempfile.gettempdir()
        filename = str(uuid.uuid4())
        out_priv = os.path.join(tmp, '{}.scrypt'.format(filename))
        out_pub = os.path.join(tmp, '{}.pub'.format(filename))
        passphrase = 'foobarbaz'
        (pub, priv) = rsa.newkeys(512)
        private_key = priv.save_pkcs1()
        public_key = pub.save_pkcs1()
        save_keys(private_key, public_key, passphrase, out_priv, out_pub)
        self.assertTrue(os.path.exists(out_priv))
        self.assertTrue(os.path.exists(out_pub))
        with self.assertRaises(ValueError):
            get_keys('incorrect_passphrase', out_priv, out_pub)

    def test_get_keys_with_file_paths(self):
        """
        Ensure that the function attempts to read from from passed in file
        paths.
        """
        tmp = tempfile.gettempdir()
        filename = str(uuid.uuid4())
        out_priv = os.path.join(tmp, '{}.scrypt'.format(filename))
        out_pub = os.path.join(tmp, '{}.pub'.format(filename))
        passphrase = 'foobarbaz'
        (pub, priv) = rsa.newkeys(512)
        private_key = priv.save_pkcs1()
        public_key = pub.save_pkcs1()
        save_keys(private_key, public_key, passphrase, out_priv, out_pub)
        self.assertTrue(os.path.exists(out_priv))
        self.assertTrue(os.path.exists(out_pub))
        actual_private, actual_public = get_keys(passphrase, out_priv,
                                                 out_pub)
        self.assertEqual(private_key, actual_private)
        self.assertEqual(public_key, actual_public)

    def test_save_keys(self):
        """
        Ensures that both the public and privte RSA keys are appropriately
        stored on the filesystem in the expected places. Furthermore, the
        private key is saved using the scrypt module that is protected by a
        passphrase.
        """
        tmp = tempfile.gettempdir()
        filename = str(uuid.uuid4())
        out_priv = os.path.join(tmp, '{}.scrypt'.format(filename))
        out_pub = os.path.join(tmp, '{}.pub'.format(filename))
        passphrase = 'foobarbaz'
        (pub, priv) = rsa.newkeys(512)
        private_key = priv.save_pkcs1()
        public_key = pub.save_pkcs1()
        save_keys(private_key, public_key, passphrase, out_priv, out_pub)
        self.assertTrue(os.path.exists(out_priv))
        self.assertTrue(os.path.exists(out_pub))
        actual_private, actual_public = get_keys(passphrase, out_priv,
                                                 out_pub)
        self.assertEqual(private_key, actual_private)
        self.assertEqual(public_key, actual_public)

    def test_get_whoami_with_path(self):
        """
        Ensure that a dict is returned from reading a file from a given
        location.
        """
        mock_fd = mock.MagicMock
        mock_fd.read = mock.MagicMock(return_value='{}')
        path = '/foo/bar.json'
        with mock.patch('builtins.open', return_value=mock_fd) as mock_open:
            result = get_whoami(path)
            self.assertIsInstance(result, dict)
            self.assertEqual({}, result)
            mock_open.assert_called_once_with(path, 'r')

    def test_get_whoami_default_path(self):
        """
        Ensure that a dict is returned from reading a file in the default
        location.
        """
        mock_fd = mock.MagicMock
        mock_fd.read = mock.MagicMock(return_value='{}')
        path = os.path.join(data_dir(), 'whoami.json')
        with mock.patch('builtins.open', return_value=mock_fd) as mock_open:
            result = get_whoami()
            self.assertIsInstance(result, dict)
            self.assertEqual({}, result)
            mock_open.assert_called_once_with(path, 'r')
