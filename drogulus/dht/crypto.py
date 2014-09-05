# -*- coding: utf-8 -*-
"""
Functions for signing and verifying items sent between peers. Items are
represented by dict objects.
"""
import time
import base64
from Crypto.Hash import SHA512
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from ..version import get_version
from .messages import to_dict


def get_seal(item, private_key):
    """
    Given an item dict that represents an outgoing message, create and return
    a string representation of a "seal" - a cryptographic signature to prove
    the provenance of the message.
    """
    root_hash = _get_hash(item)
    key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(key)
    return base64.encodebytes(signer.sign(root_hash)).decode('utf-8')


def check_seal(item):
    """
    Given a message object, use the "seal" attribute - a cryptographic
    signature to prove the provenance of the message - to check it is valid.
    Returns a boolean indication of validity.
    """
    try:
        item_dict = to_dict(item)
        raw_sig = item_dict['seal']
        signature = base64.decodebytes(raw_sig.encode('utf-8'))
        public_key = RSA.importKey(item_dict['sender'])
        del item_dict['seal']
        del item_dict['message']
        root_hash = _get_hash(item_dict)
        verifier = PKCS1_v1_5.new(public_key)
        return verifier.verify(root_hash, signature)
    except:
        pass
    return False


def get_signed_item(key, value, public_key, private_key, expires=None):
    """
    Returns a copy of the passed in key/value pair that has been signed using
    the private_key and annotated with metadata (a timestamp indicating when
    the message was signed, a timestamp indicating when the item should expire,
    the drogulus version that created the item, a SHA512 key used by the DHT,
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
    root_hash = _get_hash(signed_item)
    key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(key)
    sig = base64.encodebytes(signer.sign(root_hash)).decode('utf-8')
    signed_item['signature'] = sig
    return signed_item


def verify_item(item):
    """
    Returns a boolean to indicate if the item representing a key/value can be
    verified.
    """
    try:
        ignore_fields = ['uuid', 'recipient', 'sender', 'reply_port',
                         'version', 'seal', 'message']
        for field in ignore_fields:
            if field in item:
                del item[field]
        raw_sig = item['signature']
        signature = base64.decodebytes(raw_sig.encode('utf-8'))
        public_key = RSA.importKey(item['public_key'])
        del item['signature']
        root_hash = _get_hash(item)
        verifier = PKCS1_v1_5.new(public_key)
        return verifier.verify(root_hash, signature)
    except:
        pass
    return False


def _get_hash(obj):
    """
    Returns a SHA512 object for the given object. Works in a similar fashion
    to a Merkle tree (see https://en.wikipedia.org/wiki/Merkle_tree) should
    the object be tree like in structure - but only returns the "root" hash.
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
    return SHA512.new(seed.encode('utf-8'))


def construct_key(public_key, name=''):
    """
    Given a user's public key and the human readable string to use as a key in
    the DHT this function will return a hexdigest of the sha512 hash to use as
    the actual key within the DHT.

    This ensures the provenance (public key) and meaning of the key determine
    its hash value used for DHT lookups.
    """
    key_hash = SHA512.new(public_key.encode('ascii'))
    if name:
        # If the key has a meaningful name, create a compound key based upon
        # the sha512 values of both the public_key and name.
        name_hash = SHA512.new(name.encode('utf-8'))
        compound_key = key_hash.digest() + name_hash.digest()
        compound_hash = SHA512.new(compound_key)
        return compound_hash.hexdigest()
    else:
        return key_hash.hexdigest()
