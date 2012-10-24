"""
Contains functions that work directly with the messages for cryptographically
signing / verifying.

Copyright (C) 2012 Nicholas H.Tollervey.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
import msgpack


def generate_signature(value, timestamp, name, meta, private_key):
    """
    Given the value, timestamp, name and meta values of an outgoing value
    carrying message will use the private key to generate a cryptographic hash
    to the message to be used to sign / validate the message.

    The hash is created with the private key of the person storing the
    key/value pair. It is, in turn, based upon the SHA1 hash of the SHA1 hashes
    of the 'value', 'timestamp', 'name' and 'meta' fields.

    This mechanism ensures that the public_key used in the compound key is
    valid (i.e. it creates the correct SHA1 hash) and also ensures that the
    'value', 'timestamp', 'name' and 'meta' fields have not been tampered with.
    """
    compound_hash = construct_hash(value, timestamp, name, meta)
    key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(key)
    return signer.sign(compound_hash)


def validate_signature(value, timestamp, name, meta, signature, public_key):
    """
    Uses the public key to validate the cryptographic signature based upon
    a hash of the value, timestamp, name and meta values of a value carrying
    message.
    """
    generated_hash = construct_hash(value, timestamp, name, meta)
    try:
        public_key = RSA.importKey(public_key.strip())
    except ValueError:
        # Catches malformed public keys.
        return False
    verifier = PKCS1_v1_5.new(public_key)
    return verifier.verify(generated_hash, signature)


def validate_key_value(key, message):
    """
    Given a key and associated message containing a value this function will
    return a tuple containing two fields:

    * A boolean to indicate its validity
    * An error number (in the case of a fail) or None (if success).

    The message contains a public_key field which is used to decrypt the
    message's 'hash' field into a list of SHA1 hashes of the message's 'value',
    'timestamp', 'name' and 'meta' fields. This validates the provenance of
    the data and ensures that these fields have not been tampered with.

    Furthermore, once the validity of the public_key field is proven through
    the proceeding check, the 'key' field is verified to be a SHA1 hash of
    the SHA1 hashes of the 'public_key' and 'name' fields. This ensures the
    correct key is used to locate the data in the DHT.
    """
    if not validate_signature(message.value, message.timestamp, message.name,
                              message.meta, message.sig, message.public_key):
        # Invalid signature so bail with the appropriate error number
        return (False, 6)
    # If the signature is correct then the public key must be valid. Ensure
    # that the key used to store the value in the DHT is valid.
    generated_key = construct_key(message.public_key, message.name)
    if generated_key != key:
        # The key cannot be derived from the public_key and name fields.
        return (False, 7)
    # It checks out so return truthy.
    return (True, None)


def construct_hash(value, timestamp, name, meta):
    """
    The hash is a SHA1 hash of the SHA1 hashes of the msgpack encoded 'value',
    'timetamp, 'name' and 'meta' fields (in that order).

    It ensures that the 'value', 'timestamp', 'name' and 'meta' fields have not
    been tampered with.
    """
    hashes = []
    for item in (value, timestamp, name, meta):
        packed = msgpack.packb(item)
        hashed = SHA.new(packed).hexdigest()
        hashes.append(hashed)
    compound_hashes = ''.join(hashes)
    return SHA.new(compound_hashes)


def construct_key(public_key, name=''):
    """
    Given a string representation of a user's public key and the meaningful
    name of a key in the DHT will return a hex digest of the SHA1 hash to use
    as the actual key to use within the DHT.

    This ensures that the provenance (public key) and meaning of the DHT key
    determine its value.
    """
    # Simple normalisation: no spaces or newlines around the public key
    key_hash = SHA.new(public_key.strip())
    if name:
        # If the key has a meaningful name, create a compound key based upon
        # the SHA1 values of both the public_key and name.
        name_hash = SHA.new(name)
        compound_key = key_hash.hexdigest() + name_hash.hexdigest()
        compound_hash = SHA.new(compound_key)
        return compound_hash.hexdigest()
    else:
        # Not a compound key, so just return the hash of the public_key
        return key_hash.hexdigest()
