# -*- coding: utf-8 -*-
"""
Contains functions that are used to validate the type and content of fields
in messages sent between nodes in the DHT.
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

from drogulus.constants import ERRORS


def validate_timestamp(val):
    """
    Returns a boolean indication that a field is a valid timestamp - a
    floating point number representing the time in seconds since the Epoch (so
    called POSIX time, see https://en.wikipedia.org/wiki/Unix_time).
    """
    return isinstance(val, float)


def validate_code(val):
    """
    Returns a boolean indication that an error code is valid.
    """
    return val in ERRORS.keys()


def validate_string(val):
    """
    Returns a boolean to indicate that a field is a string of some sort.
    """
    return isinstance(val, basestring)


def validate_meta(val):
    """
    Returns a boolean to indicate that a meta-data field is a dictionary of
    key / value strings.
    """
    if isinstance(val, dict):
        for k, v in val.iteritems():
            if not (validate_string(k) and validate_string(v)):
                return False
    else:
        return False
    return True


def validate_node(val):
    """
    Returns a boolean to indicate if the passed in tuple conforms to a
    specification of another node within the DHT. A valid node is a tuple with
    four items:

    * A string representation of the SHA512 ID of the node.
    * A string representation of the node's IP address.
    * An integer representation of the node's port within a valid range of
      port values.
    * A string representation of the version of Drogulus the remote node
      conforms to.
    """
    if isinstance(val, tuple):
        if len(val) == 4:
            valid_id = validate_string(val[0])
            valid_adr = validate_string(val[1])
            valid_version = validate_string(val[3])
            port = val[2]
            if isinstance(port, int):
                return (valid_id and valid_adr and valid_version and
                        (port >= 0 and port <= 49151))
    return False


def validate_nodes(val):
    """
    Returns a boolean to indicate that a field is a tuple that may contain
    information about nodes.
    """
    if isinstance(val, tuple):
        for node in val:
            if not validate_node(node):
                return False
    else:
        return False
    return True


def validate_value(val):
    """
    Returns a boolean to indicate that a value stored in the DHT is valid.
    Currently *all* values are valid although in the future, size may be
    limited.
    """
    return True

"""
Lookup for the correct validation function for each type of field a message
may contain. Explicit is better than implicit (Zen of Python).
"""
VALIDATORS = {
    'uuid': validate_string,
    'node': validate_string,
    'code': validate_code,
    'title': validate_string,
    'details': validate_meta,
    'version': validate_string,
    'key': validate_string,
    'value': validate_value,
    'timestamp': validate_timestamp,
    'expires': validate_timestamp,
    'public_key': validate_string,
    'name': validate_string,
    'meta': validate_meta,
    'sig': validate_string,
    'nodes': validate_nodes
}
