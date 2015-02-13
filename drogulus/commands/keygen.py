# -*- coding: utf-8 -*-
"""
Defines the command for generating an RSA keypair for use with the drogulus.
"""
from cliff.command import Command
import rsa
from .utils import data_dir, APPNAME, save_keys
import getpass
import os


class KeyGen(Command):
    """
    Generates appropriate files containing the user's public/private key pair
    for use with the drogulus.

    This command will prompt the user for a passphrase to ensure the resulting
    private key file is encrypted.
    """

    def get_description(self):
        return 'Generates an RSA keypair for use with the drogulus.'

    def get_parser(self, prog_name):
        parser = super(KeyGen, self).get_parser(prog_name)
        parser.add_argument('size', nargs='?', default=4096, type=int,
                            help='The key size (default is 4096).')
        return parser

    def take_action(self, parsed_args):
        passphrase = getpass.getpass('Passphrase (make it tricky): ')
        confirm = getpass.getpass('Confirm passphrase: ')
        if passphrase != confirm:
            raise ValueError('Passphrase and confirmation did not match.')
        size = parsed_args.size
        print('Generating keys (this may take some time, go have a coffee).')
        (pub, priv) = rsa.newkeys(size)
        output_file_pub = os.path.join(data_dir(), '{}.pub'.format(APPNAME))
        output_file_priv = os.path.join(data_dir(),
                                        '{}.scrypt'.format(APPNAME))
        private_key = priv.save_pkcs1().decode('ascii')
        public_key = pub.save_pkcs1().decode('ascii')
        save_keys(private_key, public_key, passphrase, output_file_priv,
                  output_file_pub)
        print('Private key written to {}'.format(output_file_priv))
        print('Public key written to {}'.format(output_file_pub))
