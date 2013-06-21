# -*- coding: utf-8 -*-
"""
Contains generic utillity functions used in various different parts of
Drogulus.
"""

# Copyright (C) 2012-2013 Nicholas H.Tollervey.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


def long_to_hex(raw):
    """
    Given a raw numeric value (like a node's ID for example) returns it
    expressed as a hexadecimal string.
    """
    # Turn it into hex string (remembering to drop the '0x' at the start).
    as_hex = hex(raw)[2:]
    # If the integer is 'long' knock off the 'L'.
    if as_hex[-1] == 'L':
        as_hex = as_hex[:-1]
    # If required, correct length by appending 'padding' zeros.
    if len(as_hex) % 2 != 0:
        as_hex = '0' + as_hex
    as_hex = as_hex.decode('hex')
    return as_hex


def hex_to_long(raw):
    """
    Given a hexadecimal string representation of a number (like a key or
    node's ID for example) returns the numeric (long) value.
    """
    return long(raw.encode('hex'), 16)


def distance(key_one, key_two):
    """
    Calculate the XOR result between two string variables returned as a long
    type value.
    """
    val_key_one = hex_to_long(key_one)
    val_key_two = hex_to_long(key_two)
    return val_key_one ^ val_key_two
