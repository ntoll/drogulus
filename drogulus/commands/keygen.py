# -*- coding: utf-8 -*-
"""
Defines the command for generating an RSA keypair for use with the drogulus.
"""
from Crypto.PublicKey import RSA
from Crypto import Random
from cliff.command import Command
from .utils import data_dir
import getpass
import os


class KeyGen(Command):
    """
    Generates an appropriate .pem file containing the user's public/private
    key pair for use with the drogulus.

    This command will prompt the user for a passphrase to ensure the resulting
    .pem file is encrypted.
    """

    def get_description(self):
        return 'Generates an RSA keypair for use with the drogulus.'

    def get_parser(self, prog_name):
        parser = super(KeyGen, self).get_parser(prog_name)
        parser.add_argument('size', nargs='?', default=4096, type=int,
                            help='The key size (default is 4096).')
        return parser

    def take_action(self, parsed_args):
        while True:
            passphrase = getpass.getpass('Passphrase (make it tricky): ')
            confirm = getpass.getpass('Confirm passphrase: ')
            if passphrase == confirm:
                break
            else:
                print('Passphrase and confirmation did not match.')
                print('Please try again...')
        size = parsed_args.size
        output_file = os.path.join(data_dir(), 'drogulus.pem')
        print('Generating key...')
        random_generator = Random.new().read
        key = RSA.generate(size, random_generator)
        with open(output_file, 'w') as f:
            f.write(key.exportKey('PEM', passphrase).decode('ascii'))
        print('Key written to {}'.format(output_file))
