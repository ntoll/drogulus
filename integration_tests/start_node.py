"""
Runs integration tests against a single running instance of a node on the
drogulus.
"""
import sys
import os
import logging
import asyncio
from Crypto.PublicKey import RSA
from Crypto import Random
sys.path.append(os.path.join('..', 'drogulus'))
from drogulus.node import Drogulus
from drogulus.net.netstring import NetstringConnector, NetstringProtocol


def get_keypair():
    """
    Returns a (private, public) key pair as two strings.
    """
    random_generator = Random.new().read
    key = RSA.generate(1024, random_generator)
    return (key.exportKey('PEM').decode('ascii'),
            key.publickey().exportKey('PEM').decode('ascii'))


def start_node(logfile, port):
    """
    Starts a local drogulus node using throw away keys, logging to the
    referenced directory and listening on the referenced port.

    Return the Process encapsulating this node.
    """
    handler = logging.FileHandler(logfile)
    f = ' '.join(['%(asctime)s', '%(processName)-10s', '%(name)s',
                 '%(levelname)-8s', '%(message)s'])
    formatter = logging.Formatter(f)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    root.info('Starting node in new process')
    event_loop = asyncio.get_event_loop()
    connector = NetstringConnector(event_loop)
    private_key, public_key = get_keypair()
    instance = Drogulus(private_key, public_key, event_loop, connector, port)

    def protocol_factory(connector=connector, node=instance._node):
        """
        Returns an appropriately configured NetstringProtocol object for
        each connection.
        """
        return NetstringProtocol(connector, node)

    setup_server = event_loop.create_server(protocol_factory, port=port)
    event_loop.run_until_complete(setup_server)
    event_loop.run_forever()


if __name__ == '__main__':
    """
    Start node.
    """
    port = int(sys.argv[1])
    logfile = sys.argv[2]
    start_node(logfile, port)
