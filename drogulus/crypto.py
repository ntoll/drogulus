# -*- coding: utf-8 -*-
"""
Contains functions for cryptographically signing / verifying.
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

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA512
from Crypto.Signature import PKCS1_v1_5
import msgpack


def construct_hash(value, timestamp, expires, name, meta):
    """
    The hash is a SHA512 hash of the combined SHA512 hashes of the msgpack 
    encoded 'value', 'timetamp, 'expires', 'name' and 'meta' fields (in 
    that order).

    It ensures that the 'value', 'timestamp', 'expires', 'name' and 'meta'
    fields have not been tampered with.
    """
    hashes = []
    for item in (value, timestamp, expires, name, meta):
        packed = msgpack.packb(item)
        hashed = SHA512.new(packed).digest()
        hashes.append(hashed)
    compound_hashes = ''.join(hashes)
    return SHA512.new(compound_hashes)


def construct_key(public_key, name=''):
    """
    Given a string representation of a user's public key and the human 
    readable string to use as a key in the DHT this function will return a 
    digest of the SHA512 hash to use as the actual key to use within the DHT.

    This ensures that the provenance (public key) and meaning of the key
    determine its value in the DHT.
    """
    # Simple normalisation: no spaces or newlines around the public key
    key_hash = SHA512.new(public_key.strip())
    if name:
        # If the key has a meaningful name, create a compound key based upon
        # the SHA512 values of both the public_key and name.
        name_hash = SHA512.new(name)
        compound_key = key_hash.digest() + name_hash.digest()
        compound_hash = SHA512.new(compound_key)
        return compound_hash.digest()
    else:
        # Not a compound key, so just return the hash of the public_key
        return key_hash.digest()


def generate_signature(value, timestamp, expires, name, meta, private_key):
    """
    Given the value, timestamp, expires, name and meta values of an outgoing
    value carrying message will use the private key to generate a
    cryptographic hash to the message to be used to sign / validate the
    message. 
    
    This ensures that the 'value', 'timestamp', 'expires', 'name' and 'meta'
    fields have not been tampered with.

    The hash is created with the private key of the person storing the
    key/value pair. It is, in turn, based upon the SHA512 hash of the SHA512
    hashes of the 'value', 'timestamp', 'expires', 'name' and 'meta' fields.
    """
    compound_hash = construct_hash(value, timestamp, expires, name, meta)
    key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(key)
    return signer.sign(compound_hash)


def validate_signature(value, timestamp, expires, name, meta, signature,
                       public_key):
    """
    Uses the public key to validate the cryptographic signature based upon
    a hash of the values in the 'value', 'timestamp', 'expires', 'name' and
    'meta' fields of a value carrying message.
    """
    generated_hash = construct_hash(value, timestamp, expires, name, meta)
    try:
        public_key = RSA.importKey(public_key.strip())
    except ValueError:
        # Catches malformed public keys.
        return False
    verifier = PKCS1_v1_5.new(public_key)
    return verifier.verify(generated_hash, signature)


def validate_message(message):
    """
    Given a message containing a key and value this function will return a
    tuple containing two fields:

    * A boolean to indicate its validity
    * An error number (in the case of a fail) or None (if success).

    The message contains a public_key field which is used to validate the
    message's 'sig' field with a list of SHA512 hashes of the message's
    'value', 'timestamp', 'name' and 'meta' fields. This proves the
    provenance of the data and ensures that these fields have not been
    tampered with.

    Furthermore, once the validity of the public_key field is proven through
    the proceeding check, the 'key' field is verified to be a SHA512 hash of
    the SHA512 hashes of the 'public_key' and 'name' fields. This ensures the
    correct key is used to locate the data in the DHT.
    """
    if not validate_signature(message.value, message.timestamp,
                              message.expires, message.name, message.meta,
                              message.sig, message.public_key):
        # Invalid signature so bail with the appropriate error number
        return (False, 6)
    # If the signature is correct then the public key must be valid. Ensure
    # that the key used to store the value in the DHT is valid.
    generated_key = construct_key(message.public_key, message.name)
    if generated_key != message.key:
        # The key cannot be derived from the public_key and name fields.
        return (False, 7)
    # It checks out so return truthy.
    return (True, None)
