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
from drogulus.net.http import HttpConnector, HttpRequestHandler, make_http_handler


PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICYAIBAAKBgQC8jS8lvazStqe5l2rWbUgRb+vgxqbB7mAuBd0zSlfEHQdLzhk5
Wo7JrVVJ4pKK/+uuVEr7KAnnuPH2GJBQOTJGw3Z2ZgkaifMGhKIk+xBHxPDC/BCZ
JrMyKylJSz7LGwmJHYfJUGTNq9xwZfigcmthA4Vh9g7WWzmOFNdGrbufAQIDAQAB
AoGAAkUc3TJ0YzEJweU9xwkXxgX37APYPBt3kvZFHHn3pofG77WyfgtGDs2EalhM
9VlxZ+7h3DY2MFD8sL7I82vYY4Mb3OUVU1C/aWXEO4vk8LdXKn4rlV8xuFVKQn8p
DIdMIW9h7j7EbLjdbG9tlGz++b3KQ00JD5Xk+MkoN4IpXfECRQDVpKedjsdAjVCS
WtXSBu9L+QzLndj1d4gCgcO8tOrrdQ7WhwiXvI6FHgkfU5px0UBg9LEeMPTRNpWj
f/W1MmdHQSlLbQI9AOHvA7mMXLk8QHoKLPi1ZgJo96SpX1bFNBqkUuXGYici4A1T
ud+V0/wbnRHzZ9DHfDFKjoLlfybHK2UxZQJEPksNSIaKGItb0+DCecPl4EwU7AXx
bdlVgg2eKhbCbLcsBWdIHR4wnCXe2RCCdu9hiyOtxTTXHW2CAjNcTGIO9RrN1J0C
PQC2JsIlBQH4oZgGDFAnj/AXP1Nw4NCpn0IbvKHM+H1HujlS5U608RHAbu7aexgW
3c3F26s74xT5SZg19HUCRGgX01UT/sukk4ALuFCfwuR0hodIbhuJ6eWh/n0VEXJ4
Zt47JXvqWbVjC6vtSgBM5LiRAxcfee7Bi94OtZik4vI132d4
-----END RSA PRIVATE KEY-----"""


PUBLIC_KEY = """-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBALyNLyW9rNK2p7mXatZtSBFv6+DGpsHuYC4F3TNKV8QdB0vOGTlajsmt
VUnikor/665USvsoCee48fYYkFA5MkbDdnZmCRqJ8waEoiT7EEfE8ML8EJkmszIr
KUlLPssbCYkdh8lQZM2r3HBl+KBya2EDhWH2DtZbOY4U10atu58BAgMBAAE=
-----END RSA PUBLIC KEY-----"""


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
    instance = Drogulus(PRIVATE_KEY, PUBLIC_KEY, event_loop, connector, port)
    app = make_http_handler(event_loop, connector, instance, None)
    f = event_loop.create_server(app, '0.0.0.0', 8080)
    srv = event_loop.run_until_complete(f)
    try:
        event_loop.run_forever()
    except KeyboardInterrup:
        pass

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
