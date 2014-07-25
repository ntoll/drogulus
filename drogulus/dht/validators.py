# -*- coding: utf-8 -*-
"""
Contains functions that are used to validate the type and content of fields
in messages sent between nodes in the DHT.
"""


def validate_timestamp(val):
    """
    Returns a boolean indication that a field is a valid timestamp - a
    floating point number representing the time in seconds since the Epoch (so
    called POSIX time, see https://en.wikipedia.org/wiki/Unix_time).
    """
    return (isinstance(val, float) and val >= 0.0)


def validate_port(val):
    """
    Check the port is an integer and within the valid range of allowed ports.
    """
    return (isinstance(val, int) and (val >= 0 and val <= 49151))


def validate_string(val):
    """
    Returns a boolean to indicate that a field is a string of some sort.
    """
    return isinstance(val, str)


def validate_dict(val):
    """
    Returns a boolean to indicate that a field is a dictionary of some sort.
    """
    return isinstance(val, dict)


def validate_node(val):
    """
    Returns a boolean to indicate if the passed in tuple conforms to a
    specification of another node within the DHT. A valid node is a tuple with
    four items:

    * A string representation of the node's public key.
    * A string representation of the version of Drogulus the remote node
      conforms to.
    * A string representation of the URI identifying how to connect to the
      remote note.
    """
    if isinstance(val, tuple):
        if len(val) == 3:
            valid_public_key = validate_string(val[0])
            valid_version = validate_string(val[1])
            valid_uri = validate_string(val[2])
            return valid_public_key and valid_version and valid_uri
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
    'recipient': validate_string,
    'sender': validate_string,
    'version': validate_string,
    'seal': validate_string,
    'error': validate_string,
    'details': validate_string,
    'key': validate_string,
    'value': validate_value,
    'timestamp': validate_timestamp,
    'expires': validate_timestamp,
    'created_with': validate_string,
    'public_key': validate_string,
    'name': validate_string,
    'signature': validate_string,
    'nodes': validate_nodes,
    'reply_port': validate_port
}
