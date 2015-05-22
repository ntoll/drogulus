# -*- coding: utf-8 -*-
"""
Functions for signing and verifying items sent between peers. Items are
represented by dict objects.
"""
import time
import binascii
import rsa
from hashlib import sha512
from ..version import get_version
from .messages import to_dict


def get_seal(item, private_key):
    """
    Given an item dict that represents an outgoing message, create and return
    a string representation of a "seal" - a cryptographic signature to prove
    the provenance of the message.
    """
    root_hash = _get_hash(item).hexdigest()
    key = rsa.PrivateKey.load_pkcs1(private_key.encode('ascii'))
    return binascii.hexlify(rsa.sign(root_hash.encode('ascii'),
                                     key, 'SHA-512')).decode('ascii')


def check_seal(item):
    """
    Given a message object, use the "seal" attribute - a cryptographic
    signature to prove the provenance of the message - to check it is valid.
    Returns a boolean indication of validity.
    """
    try:
        item_dict = to_dict(item)
        raw_sig = item_dict['seal']
        signature = binascii.unhexlify(raw_sig.encode('ascii'))
        key = rsa.PublicKey.load_pkcs1(item_dict['sender'].encode('ascii'))
        del item_dict['seal']
        del item_dict['message']
        root_hash = _get_hash(item_dict).hexdigest()
        return rsa.verify(root_hash.encode('ascii'), signature, key)
    except:
        pass
    return False


def get_signed_item(key, value, public_key, private_key, expires=None):
    """
    Returns a copy of the passed in key/value pair that has been signed using
    the private_key and annotated with metadata (a timestamp indicating when
    the message was signed, a timestamp indicating when the item should expire,
    the drogulus version that created the item, a sha512 key used by the DHT,
    the public_key and the signature).

    The expiration timestamp is derived by adding the (optional) expires
    number of seconds to the timestamp. If no expiration is specified then the
    "expires" value is set to 0.0 (expiration is expressed as a float).
    """
    signed_item = {
        'name': key,
        'value': value,
        'created_with': get_version(),
        'public_key': public_key,
        'timestamp': time.time(),
        'key': construct_key(public_key, key)
    }
    expires_at = 0.0  # it's a float, dammit
    t = type(expires)
    if expires and (t == int or t == float) and expires > 0.0:
        expires_at = signed_item['timestamp'] + expires
    signed_item['expires'] = expires_at
    root_hash = _get_hash(signed_item).hexdigest()
    key = rsa.PrivateKey.load_pkcs1(private_key.encode('ascii'))
    sig = binascii.hexlify(rsa.sign(root_hash.encode('ascii'), key,
                                    'SHA-512')).decode('ascii')
    signed_item['signature'] = sig
    return signed_item


def verify_item(raw_item):
    """
    Returns a boolean to indicate if the item representing a key/value can be
    verified.
    """
    item = raw_item.copy()
    try:
        ignore_fields = ['uuid', 'recipient', 'sender', 'reply_port',
                         'version', 'seal', 'message']
        for field in ignore_fields:
            if field in item:
                del item[field]
        raw_sig = item['signature']
        signature = binascii.unhexlify(raw_sig.encode('ascii'))
        key = rsa.PublicKey.load_pkcs1(item['public_key'].encode('ascii'))
        del item['signature']
        root_hash = _get_hash(item).hexdigest()
        return rsa.verify(root_hash.encode('ascii'), signature, key)
    except:
        pass
    return False


def _get_hash(obj):
    """
    Returns a sha512 hexdigest for the given object. Works in a similar fashion
    to a Merkle tree (see https://en.wikipedia.org/wiki/Merkle_tree) but only
    returns the "root" hash.
    """
    obj_type = type(obj)
    if obj_type is dict:
        hash_list = []
        for k in sorted(obj):
            hash_list.append(_get_hash(k).hexdigest())
            hash_list.append(_get_hash(obj[k]).hexdigest())
        seed = ''.join(hash_list)
    elif obj_type is list:
        hash_list = []
        for item in obj:
            hash_list.append(_get_hash(item).hexdigest())
        seed = ''.join(hash_list)
    elif obj_type is bool:
        seed = str(obj).lower()
    elif obj_type is float:
        seed = repr(obj)
    elif obj is None:
        seed = 'null'
    else:
        seed = str(obj)
    return sha512(seed.encode('ascii'))


def construct_key(public_key, name=''):
    """
    Given a user's public key and the human readable string to use as a key in
    the DHT this function will return a hexdigest of the sha512 hash to use as
    the actual key within the DHT.

    This ensures the provenance (public key) and meaning of the key determine
    its hash value used for DHT lookups.
    """
    key_hash = sha512(public_key.encode('ascii'))
    if name:
        # If the key has a meaningful name, create a compound key based upon
        # the sha512 values of both the public_key and name.
        name_hash = sha512(name.encode('utf-8'))
        compound_key = key_hash.digest() + name_hash.digest()
        compound_hash = sha512(compound_key)
        return compound_hash.hexdigest()
    else:
        return key_hash.hexdigest()
