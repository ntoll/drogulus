# -*- coding: utf-8 -*-
"""
Ensures the WhoAmI class works as expected.
"""
import unittest
import os
import os.path
from drogulus.commands.whoami import WhoAmI
from drogulus.commands.utils import data_dir
from unittest import mock


class TestWhoAmI(unittest.TestCase):
    """
    Exercises the WhoAmI class (a child of cliff.command.Command) works in
    the expected manner.
    """

    def test_contact_fields(self):
        """
        Ensure the WhoAmI class has a contact_fields attribute that is a list
        containing strings.
        """
        self.assertIsInstance(WhoAmI.contact_fields, list)
        for field in WhoAmI.contact_fields:
            self.assertIsInstance(field, str)

    def test_get_description(self):
        """
        Calling the get_description method should return a non-empty string.
        """
        whoami = WhoAmI(None, None)
        result = whoami.get_description()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_take_action(self):
        """
        Ensure that the take_action method interrogates the user in the
        expected way and produces an appropriate JSON file in the expected
        location containing the expected result.
        """
        with mock.patch('builtins.input', return_value='y'):
            whoami = WhoAmI(None, None)
            with mock.patch('json.dump') as writer:
                whoami.take_action([])
                self.assertEqual(1, writer.call_count)
                output_file = os.path.join(data_dir(), 'whoami.json')
                self.assertEqual(writer.call_args[0][1].name, output_file)
