# -*- coding: utf-8 -*-
"""
Defines the command for starting a node in the drogulus.
"""
from ..node import Drogulus
from ..net.http import HttpConnector, make_http_handler
from .utils import data_dir, log_dir, get_keys, get_whoami, APPNAME
from cliff.command import Command
from getpass import getpass
import logging
import logging.handlers
import asyncio
import json
import os
import os.path


class Start(Command):
    """
    Defines the command for starting a node in the drogulus.
    """

    def get_description(self):
        return 'Starts a local drogulus node.'

    def get_parser(self, prog_name):
        parser = super(Start, self).get_parser(prog_name)
        parser.add_argument('--passphrase', '-p', nargs='?', default='',
                            type=str, help='The passphrase for the private ' +
                            'RSA key.')
        parser.add_argument('--keys', '-k', nargs='?', default='', type=str,
                            help='The directory containing the RSA public ' +
                            'and private keys.')
        parser.add_argument('--peers', nargs='?', default='', type=str,
                            help='The peer.json file used to seed the ' +
                            'local node\'s routing table.')
        parser.add_argument('--port', nargs='?', default=1908, type=int,
                            help='The incoming port (defaults to 1908).')
        parser.add_argument('--whoami', nargs='?', default='', type=str,
                            help='The whoami.json file to use to identify ' +
                            'the owner of the local node to the wider ' +
                            'network.')
        return parser

    def take_action(self, parsed_args):
        """
        Starts a local instance of the drogulus given the parsed arguments to
        use. The command falls back to sane defaults if none are given.
        """
        passphrase = parsed_args.passphrase
        if not passphrase:
            print('You must supply a passphrase.')
            passphrase = getpass().strip()
            if not passphrase:
                raise ValueError('You must supply a passphrase.')
        port = parsed_args.port
        whoami = parsed_args.whoami
        key_dir = parsed_args.keys
        peer_file = parsed_args.peers

        # Setup logging
        logfile = os.path.join(log_dir(), 'drogulus.log')
        handler = logging.handlers.TimedRotatingFileHandler(logfile,
                                                            when='midnight',
                                                            interval=1)
        f = ' '.join(['%(asctime)s', '%(processName)-10s', '%(name)s',
                     '%(levelname)-8s', '%(message)s'])
        formatter = logging.Formatter(f)
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.addHandler(handler)
        log = logging.getLogger(__name__)
        print('Logging to {}'.format(logfile))

        # RSA key config.
        priv_path = None
        pub_path = None
        if key_dir:
            priv_path = os.path.join(key_dir, '{}.scrypt'.format(APPNAME))
            pub_path = os.path.join(key_dir, '{}.pub'.format(APPNAME))
        try:
            private_key, public_key = get_keys(passphrase, priv_path,
                                               pub_path)
        except Exception as ex:
            log.error('Unable to get keys from {}'.format(key_dir))
            log.error(ex)
            raise ex

        # Whoami
        try:
            whoami = get_whoami(whoami)
        except:
            log.error('Unable to get whoami file.')
            whoami = None

        # Asyncio boilerplate.
        event_loop = asyncio.get_event_loop()
        connector = HttpConnector(event_loop)  # NetstringConnector(event_loop)
        instance = Drogulus(private_key, public_key, event_loop, connector,
                            port, whoami)
        app = make_http_handler(event_loop, connector, instance._node)
        app_task = event_loop.create_server(app, '0.0.0.0', port)
        server = event_loop.run_until_complete(app_task)

        # Join the network
        if peer_file:
            peer_details = json.load(open(peer_file))
            instance.join(peer_details)

        # Run the server
        try:
            event_loop.run_forever()
        except KeyboardInterrupt:
            log.info('Manual exit')
        finally:
            # dump peers
            if not peer_file:
                peer_file = os.path.join(data_dir(), 'peers.json')
            with open(peer_file, 'w') as output:
                json.dump(instance._node.routing_table.dump(), output,
                          indent=2)
                log.info('Dumped peers')
            log.info('STOPPED')
            server.close()
            event_loop.close()
