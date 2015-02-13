# -*- coding: utf-8 -*-
"""
Utility functions used by the various drogulus command line tools.
"""
from ..version import get_version
from ..contrib.appdirs import user_data_dir, user_log_dir
import json
import os
import pyscrypt
from pyscrypt.file import InvalidScryptFileFormat


APPNAME = 'drogulus'
APPAUTHOR = 'DrogulusProject'


def data_dir():
    """
    Returns the path to the OS appropriate user data directory for the
    drogulus application.

    If this directory does not exist it will be created.
    """
    udd = user_data_dir(APPNAME, APPAUTHOR)
    if not os.path.exists(udd):
        os.makedirs(udd)
    return udd


def log_dir():
    """
    Returns the path to the OS appropriate user log directory for the
    drogulus application.

    If this directory does not exist it will be created.
    """
    uld = user_log_dir(APPNAME, APPAUTHOR, get_version())
    if not os.path.exists(uld):
        os.makedirs(uld)
    return uld


def get_keys(passphrase, priv_file=None, pub_file=None):
    """
    Will return a string representation of both the private and public
    RSA keys found in the locations specified by priv_file and pub_file args.
    Since the private key is password protected the passphrase argument is
    used to decrypt it. If no file paths are given then sane default
    location and names are used.
    """
    if not pub_file:
        pub_file = os.path.join(data_dir(), '{}.pub'.format(APPNAME))
    if not priv_file:
        priv_file = os.path.join(data_dir(), '{}.scrypt'.format(APPNAME))
    pub = open(pub_file, 'rb').read()
    try:
        with pyscrypt.ScryptFile(priv_file, passphrase.encode('utf-8')) as f:
            priv = f.read()
    except InvalidScryptFileFormat:
        # Make the exception a bit more human.
        msg = 'Unable to read private key file. Check your passphrase!'
        raise ValueError(msg)
    return (priv, pub)


def save_keys(private_key, public_key, passphrase, priv_file, pub_file):
    """
    Given private and public keys as bytes, a passphrase and paths to private
    and public output files will save the keys in the appropriate file path
    location. In the case of the private key, will use the scrypt module (see:
    https://en.wikipedia.org/wiki/Scrypt) and the passphrase to encrypt it.
    """
    with open(pub_file, 'wb') as fpub:
        fpub.write(public_key)
    # PyScrypt has problems using the 'with' keyword and saving content.
    fp = open(priv_file, 'wb')
    try:
        fpriv = pyscrypt.ScryptFile(fp, passphrase.encode('utf-8'), N=1024,
                                    r=1, p=1)
        fpriv.write(private_key)
    finally:
        fpriv.close()


def get_whoami(input_file=None):
    """
    Attempts to get the user's whoami information.
    """
    if not input_file:
        input_file = os.path.join(data_dir(), 'whoami.json')
    return json.load(open(input_file, 'r'))
