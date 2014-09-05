# -*- coding: utf-8 -*-
"""
Utility functions used by the various drogulus command line tools.
"""
from ..version import get_version
from ..contrib.appdirs import user_data_dir, user_log_dir
from Crypto.PublicKey import RSA
import json
import os


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


def get_keys(passphrase, input_file=None):
    """
    Will return a string representation of both the private and public
    password protected RSA keys found in the location specified by input_file.
    If input_file is None then the sane default location and name is used.
    """
    if not input_file:
        input_file = os.path.join(data_dir(), '{}.pem'.format(APPNAME))
    f = open(input_file, 'r')
    key = RSA.importKey(f.read(), passphrase)
    return (key.exportKey('PEM').decode('ascii'),
            key.publickey().exportKey('PEM').decode('ascii'))


def get_whoami(input_file=None):
    """
    Attempts to get the user's whoami information.
    """
    if not input_file:
        input_file = os.path.join(data_dir(), 'whoami.json')
    return json.load(open(input_file, 'r'))


def get_alias(input_file=None):
    """
    Attempts to get the user's alias dictionary.
    """
    if not input_file:
        input_file = os.path.join(data_dir(), 'alias.json')
    return json.load(open(input_file, 'r'))
