# -*- coding: utf-8 -*-
"""
Defines the command for starting a node in the drogulus.
"""
from ..node import Drogulus
from ..net.http import HttpConnector, HttpRequestHandler
from .utils import data_dir, log_dir, get_keys, get_whoami, get_alias
from cliff.command import Command
from getpass import getpass
import logging
import asyncio
import json
import sys
import os


class Start(Command):
    """
    Defines the command for starting a node in the drogulus.
    """

    def get_description(self):
        return 'Starts a local drogulus node.'

    def get_parser(self, prog_name):
        # TODO: Non positional args
        parser = super(Start, self).get_parser(prog_name)
        parser.add_argument('--passphrase', '-p', nargs='?', default='',
                            type=str, help='The passphrase for the RSA keys.')
        parser.add_argument('--keyfile', '-k', nargs='?', default='', type=str,
                            help='The pem file of the RSA keys to use.')
        parser.add_argument('--peers', nargs='?', default='', type=str,
                            help='The peer.json file used to seed the ' +
                            'local node\'s routing table.')
        parser.add_argument('--port', nargs='?', default=1908, type=int,
                            help='The incoming port (defaults to 1908).')
        parser.add_argument('--whoami', nargs='?', default='', type=str,
                            help='The whoami.json file to use.')
        parser.add_argument('--alias', nargs='?', default='', type=str,
                            help='The alias.json file to use.')
        return parser

    def take_action(self, parsed_args):
        """
        Starts a local instance of the drogulus given the parsed arguments to
        use. The command falls back to sane defaults if none are given.
        """
        passphrase = parsed_args.passphrase
        if not passphrase:
            print('You must supply a passphrase')
            passphrase = getpass()
            if not passphrase:
                sys.exit(1)
        port = parsed_args.port
        whoami = parsed_args.whoami
        alias = parsed_args.alias
        key_file = parsed_args.keyfile
        peer_file = parsed_args.peers

        # RSA key config.
        try:
            private_key, public_key = get_keys(passphrase, key_file)
        except Exception as ex:
            print('Unable to get keys from {}'.format(key_file))
            print('{}'.format(repr(ex)))
            sys.exit(1)

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

        # Whoami and alias
        try:
            whoami = get_whoami(whoami)
        except:
            log.error('Unable to get whoami file.')
            whoami = None
        try:
            alias = get_alias(alias)
        except:
            log.error('Unable to get alias file.')
            alias = None

        # Asyncio boilerplate.
        event_loop = asyncio.get_event_loop()
        connector = HttpConnector(event_loop)  # NetstringConnector(event_loop)
        instance = Drogulus(public_key, private_key, event_loop, connector,
                            port, alias, whoami)

        def protocol_factory(connector=connector, node=instance._node):
            """
            Returns an appropriately configured NetstringProtocol object for
            each connection.
            """
            # return NetstringProtocol(connector, node)
            return HttpRequestHandler(connector, node)

        setup_server = event_loop.create_server(protocol_factory, port=port)
        server = event_loop.run_until_complete(setup_server)
        log.info('Serving on {}.'.format(server.sockets[0].getsockname()))

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
            # dump alias
            with open(os.path.join(data_dir(), 'alias.json'), 'w') as output:
                json.dump(instance.alias, output, indent=2)
                log.info('Dumped alias')
            # dump peers
            if not peer_file:
                peer_file = os.path.join(data_dir(), 'peers.json')
            with open(peer_file, 'w') as output:
                json.dump(instance._node.routing_table.all_contacts(),
                          output, indent=2)
                log.info('Dumped peers')
            log.info('STOPPED')
            server.close()
            event_loop.close()
