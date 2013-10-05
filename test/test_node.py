# -*- coding: utf-8 -*-
"""
Tests for the core Drogulus class
"""
from drogulus.node import Drogulus
import unittest


class TestDrogulus(unittest.TestCase):
    """
    Ensures the core Drogulus class works as expected.
    """

    def __init__(self):
        self.drogulus = Drogulus()
