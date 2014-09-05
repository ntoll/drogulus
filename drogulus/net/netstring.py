# -*- coding: utf-8 -*-
"""
Contains the classes used to implement the Netstring protocol. These classes
handle the network communication "down the wire" in a way that is opaque to
the local node (from its point of view, messages come in and messages go out).
"""
from ..dht.messages import to_dict, from_dict
from .connector import Connector
from hashlib import sha512
import urllib.parse
import logging
import asyncio
import json
import re


LENGTH, DATA, COMMA = range(3)
NUMBER = re.compile('(\d*)(:?)')


log = logging.getLogger(__name__)


class NetstringParseError(ValueError):
    """
    The incoming data is not in a valid Netstring format.
    """
    pass


class NetstringProtocol(asyncio.Protocol):
    """
    Implements the netstring protocol. Netstrings are defined here:

    http://cr.yp.to/proto/netstrings.txt

    ...and the Wikipedia article (https://en.wikipedia.org/wiki/Netstrings)
    contains an interesting discussion of their simplicity and capabilities.

    This implementation is heavily influenced by the NetstringReceiver
    protocol class in the Twisted project. I've used the same FSM approach and
    very similar (PEP8) names.

    The class ensures the following:

    * Messages are limited in size, useful if you don't want someone sending
      you a 500MB netstring (change the MAX_LENGTH to the maximum length you
      wish to accept).
    * The connection is dropped if an illegal message is received.
    """

    MAX_LENGTH = 1024 * 1024 * 12  # 12mb-ish
    _reader_state = LENGTH
    _reader_length = 0

    def __init__(self, connector, node):
        """
        Connector mediates between the node and the Protocol. Node is the
        local node on the network that handles incoming messages.
        """
        self._connector = connector
        self._node = node

    def string_received(self, data):
        """
        Process the raw data with the connector and local node.
        """
        peer = self.transport.get_extra_info('peername')[0]
        self._connector.receive(data, peer, self._node, self)

    def connection_made(self, transport):
        """
        Called when an incoming connection is made to this node. The transport
        argument is the means of pushing data back to the client.
        """
        self.transport = transport

    def handle_data(self):
        """
        Processes the incoming data if the current status is DATA.
        """
        buff = self.__data[:int(self._reader_length)]
        self.__data = self.__data[int(self._reader_length):]
        self._reader_length = self._reader_length - len(buff)
        self.__buffer = self.__buffer + buff
        if self._reader_length != 0:
            return
        self.string_received(self.__buffer.decode('utf-8'))
        self._reader_state = COMMA

    def handle_comma(self):
        """
        Process the incoming data if the current status if COMMA.
        """
        self._reader_state = LENGTH
        if self.__data[0] != 44:  # 44 = comma in ascii
            raise NetstringParseError(repr(self.__data))
        self.__data = self.__data[1:]

    def handle_length(self):
        """
        Process the incoming data if the current status is LENGTH.
        """
        m = NUMBER.match(self.__data.decode('utf-8'))
        if not m.end():
            raise NetstringParseError(repr(self.__data))
        self.__data = self.__data[m.end():]
        if m.group(1):
            self._reader_length = int(m.group(1))
            if self._reader_length > self.MAX_LENGTH:
                raise NetstringParseError('Netstring too long')
        if m.group(2):
            self.__buffer = b''
            self._reader_state = DATA

    def data_received(self, data):
        """
        Called whenever the local node receives data from the remote peer.
        """
        self.__data = data
        try:
            while self.__data:
                if self._reader_state == DATA:
                    self.handle_data()
                elif self._reader_state == COMMA:
                    self.handle_comma()
                elif self._reader_state == LENGTH:
                    self.handle_length()
                else:
                    msg = 'Netstring mode is not DATA, COMMA or LENGTH'
                    raise RuntimeError(msg)
        except NetstringParseError:
            self.transport.close()

    def send_string(self, data):
        """
        Encodes and sends a string of data to the node at the other end of
        self.transport.
        """
        length = len(data.encode('utf-8'))
        output = '{}:{},'.format(length, data)
        self.transport.write(output.encode('utf-8'))


class NetstringConnector(Connector):
    """
    A connector child class that brokers between the netstring network-y end
    of things and the local node within the DHT network.
    """

    def __init__(self, event_loop):
        """
        Initialises the object with an empty cache to contain protocol objects
        associated with peers. The passed in event_loop is used to create
        connections to the remote peers in the network.
        """
        self._connections = {}
        self.event_loop = event_loop

    def _send_message_with_protocol(self, message, protocol):
        """
        Sends the referenced message to the remote peer using the passed in
        protocol object.
        """
        protocol.send_string(json.dumps(to_dict(message)))

    def send(self, contact, message, sender):
        """
        Sends the message to the referenced contact.
        """
        delivered = asyncio.Future()
        if contact.network_id in self._connections:
            # Use the cached protocol object.
            protocol = self._connections[contact.network_id]
            try:
                self._send_message_with_protocol(message, protocol)
                delivered.set_result(True)
                return delivered
            except:
                # Continue and retry with a fresh connection. E.g. perhaps
                # the transport dropped but the remote peer is still online.
                # Clean up the old protocol object.
                del self._connections[contact.network_id]
        # Create a new connection and then cache it.
        uri = urllib.parse.urlsplit(contact.uri)
        protocol = lambda: NetstringProtocol(self, sender)
        coro = self.event_loop.create_connection(protocol, uri.hostname,
                                                 uri.port)
        connection = asyncio.Task(coro)

        def on_connect(task, contact=contact, message=message, nc=self,
                       delivered=delivered):
            """
            Once a connection is established handles the sending of the
            actual message and caching of the protocol for later use.
            """
            try:
                if task.result():
                    protocol = task.result()[1]
                    nc._send_message_with_protocol(message, protocol)
                    nc._connections[contact.network_id] = protocol
                    delivered.set_result(True)
            except Exception as ex:
                # There was a problem so pass up the callback chain for
                # upstream to handle what to do (e.g. punish the problem
                # remote peer).
                delivered.set_exception(ex)

        connection.add_done_callback(on_connect)
        return delivered

    def receive(self, raw, sender, handler, protocol):
        """
        Called when a message is received from a remote node on the network.
        """
        try:
            message_dict = json.loads(raw)
            message = from_dict(message_dict)
            network_id = sha512(message.sender.encode('ascii')).hexdigest()
            reply = handler.message_received(message, 'netstring', sender,
                                             message.reply_port)
            if reply:
                self._send_message_with_protocol(reply, protocol)
            # Cache the connection.
            if network_id not in self._connections:
                # If the remote node is a new peer cache the protocol.
                self._connections[network_id] = protocol
            elif self._connections[network_id] != protocol:
                # If the remote node has a cached protocol that appears to
                # have expired cache the replacement protocol object.
                self._connections[network_id] = protocol
        except Exception as ex:
            # There's not a lot that can be usefully done at this stage except
            # to log the problem in a way that may aid further investigation.
            log.error('Problem message received from {}'.format(sender))
            log.exception(ex)
            log.error(raw)
