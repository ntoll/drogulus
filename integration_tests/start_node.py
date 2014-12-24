"""
Runs integration tests against a single running instance of a node on the
drogulus.
"""
import sys
import os
import logging
import asyncio
sys.path.append(os.path.join('..', 'drogulus'))
from drogulus.node import Drogulus
from drogulus.net.http import HttpConnector, HttpRequestHandler


PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQC+VBkfaJzgR3ajbC6L5VGlErDoxKsIcwVYlEJyYsO6rG4PSHsc
KeG1JvUdYPGJ+YAmDW4iBe1bpJex1WLhXcwPWmx+SV1OcLM7+7q/MkaUykn83tSv
z8Fkdl7UEAdpQrr7vXuhNvc7nCf6rHQAhdnrtsIZzxLd7Q9A1fSNVFd+NwIDAQAB
AoGBAKjerTu08hv8zELLpbDyUrKIFvcwKCBjDYc+ZIZhIxDqFOzyfmjKsDyuyCS8
8xJckVsx51nAsIzzSLS8g/M56ebdBD1PrxKmKh5kTzV68qjzwx6QrjPSIbEhedRY
rvuLSGJurwHCRkPcyZ2022AOpdl8sEknu7DKoGJXQD9fLNxhAkEAz8QqEDll4zGJ
kDnSBbmgncU7R29umwHDkR40qhe98Q6ELdiYnioihaiMqPOYnUG9qYEvlCktHa9A
CZ9HqcAjEwJBAOqDlXOszNQsUfC8UWJm7wnlg6Ozorrli+zmXLb7QXi3RazmEuSq
fAa/ahNhmgAzje2nK2NOmFJWUC/NSr2b+M0CQD3uHBev9EXvizC5e3gHZ+//TXcy
qQZ9VR0Zotscrpp/GDlOOdfTeWzb2+m0isY9RVqUTmlciL0zcuQrXUIlKo8CQG2z
ifjnj5V8+gO0BBoU7qLhg1fTkz78XB1AkYRjOng+u1Aq/BGNkqERb4yLbp/DfhP6
zDgTLvvtNmt2DA1wZc0CQEQWWSTbBE9PZAKcXvpX/ns036vm5/vcPIfuvl7r6B6e
pi2VxsKNY6e+Xbs0CoEPOowy3TU3JGHgpoCDDGa7XgA=
-----END RSA PRIVATE KEY-----"""


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+VBkfaJzgR3ajbC6L5VGlErDo
xKsIcwVYlEJyYsO6rG4PSHscKeG1JvUdYPGJ+YAmDW4iBe1bpJex1WLhXcwPWmx+
SV1OcLM7+7q/MkaUykn83tSvz8Fkdl7UEAdpQrr7vXuhNvc7nCf6rHQAhdnrtsIZ
zxLd7Q9A1fSNVFd+NwIDAQAB
-----END PUBLIC KEY-----"""


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
    connector = HttpConnector(event_loop)
    instance = Drogulus(PUBLIC_KEY, PRIVATE_KEY, event_loop, connector, port)

    def protocol_factory(connector=connector, node=instance._node):
        """
        Returns an appropriately configured NetstringProtocol object for
        each connection.
        """
        return HttpRequestHandler(connector, node)

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
