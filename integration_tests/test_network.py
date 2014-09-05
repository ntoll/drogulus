"""
Starts a network of 30 nodes running on the local machine. Each node joins
the network and sets then gets a value.

If there are no ERROR messages in the log file then we assume things have
worked as expected.
"""
import sys
import os
import tempfile
import uuid
import logging
import asyncio
from Crypto.PublicKey import RSA
from Crypto import Random
sys.path.append(os.path.join('..', 'drogulus'))
from drogulus.node import Drogulus
from drogulus.dht.contact import PeerNode
from drogulus.net.netstring import NetstringConnector, NetstringProtocol


SIZE = 30


def get_logfile():
    """
    Returns a string identifying the temporary location of a randomly named
    log file to use and tail during the integration tests.
    """
    logfilename = ''.join(['drogulus_test', str(uuid.uuid4().hex), '.log'])
    return os.path.join(tempfile.gettempdir(), logfilename)


def get_keypair():
    """
    Returns a (private, public) key pair as two strings.
    """
    random_generator = Random.new().read
    key = RSA.generate(1024, random_generator)
    return (key.exportKey('PEM').decode('ascii'),
            key.publickey().exportKey('PEM').decode('ascii'))


def start_node(event_loop, port):
    """
    Starts a local drogulus node using throw away keys, logging to the
    referenced directory and listening on the referenced port.

    Return the Process encapsulating this node.
    """
    connector = NetstringConnector(event_loop)
    private_key, public_key = get_keypair()
    instance = Drogulus(public_key, private_key, event_loop, connector, port)

    def protocol_factory(connector=connector, node=instance._node):
        """
        Returns an appropriately configured NetstringProtocol object for
        each connection.
        """
        return lambda: NetstringProtocol(connector, node)

    factory = protocol_factory()
    setup_server = event_loop.create_server(factory, port=port)
    event_loop.run_until_complete(setup_server)
    return instance


@asyncio.coroutine
def set_value(node, key, value):
    """
    Sets a value to the node.
    """
    yield from node.set(key, value)


def show_result(task):
    """
    Prints the result
    """
    print(task.result())


if __name__ == '__main__':
    logfile = get_logfile()
    print('Logging to {}'.format(logfile))
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
    nodes = []
    for i in range(SIZE):
        node = start_node(event_loop, 8000+i)
        nodes.append(node)
    genesis_node = nodes[0]

    for node in nodes[1:]:
        url = 'netstring://127.0.0.1:%d' % genesis_node._node.reply_port
        p = PeerNode(genesis_node.public_key, genesis_node.whoami['version'],
                     url)
        peers = [p, ]
        t = node.join(peers)

        def on_join(joined, node=node):
            setter = node.set('foo', 'bar')

            def on_set(x, node=node):
                getter = node.get(node.whoami['public_key'], 'foo')
                getter.add_done_callback(show_result)

            setter.add_done_callback(on_set)

        t.add_done_callback(on_join)

    try:
        event_loop.run_forever()
    finally:
        event_loop.close()
