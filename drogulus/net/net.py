# -*- coding: utf-8 -*-
"""
Contains a definition of the low-level networking protocol used by the DHT
(and related functionality).
"""

# Copyright (C) 2012 Nicholas H.Tollervey.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet import protocol
from twisted.python import log
from twisted.protocols.basic import NetstringReceiver
from messages import Error, to_msgpack, from_msgpack
from constants import ERRORS
from drogulus.version import get_version
from uuid import uuid4


class TimeoutError(Exception):
    """
    Raised when an RPC times out.
    """
    pass


class DHTProtocol(NetstringReceiver):
    """
    The low level networking protocol.

    Msgpack (http://msgpack.org/) encoded payloads are transported as
    netstrings (http://cr.yp.to/proto/netstrings.txt).

    The payload is simply a dictionary of attributes. Please see the classes
    representing each type of request/response type for what these attributes
    represent.

    To the external world messages come in, messages go out (and implementation
    details are hidden).
    """

    def except_to_error(self, exception):
        """
        Given a Python exception will return an appropriate Error message
        instance.
        """
        if isinstance(exception, Exception) and len(exception.args) == 4:
            # Exception includes all the information we need.
            uuid = exception.args[3]
            code = exception.args[0]
            title = exception.args[1]
            details = exception.args[2]
        else:
            uuid = str(uuid4())
            code = 3
            title = ERRORS[code]
            details = {}
        return Error(uuid, self.factory.node.id, code, title, details,
                     get_version())

    def stringReceived(self, raw):
        """
        Handles incoming requests by unpacking them and instantiating the
        correct request class before passing them to the Node instance for
        further processing. If the message cannot be unpacked or is invalid
        an appropriate error message is returned to the originating caller.
        """
        try:
            message = from_msgpack(raw)
            self.factory.node.message_received(message, self)
        except Exception, ex:
            # Catch all for anything unexpected
            log.msg('ERROR')
            log.msg(ex)
            self.sendMessage(self.except_to_error(ex), True)

    def sendMessage(self, msg, loseConnection=False):
        """
        Sends the referenced message to the connected peer on the network. If
        loseConnection is set to true the connection will be dropped once the
        message has been sent.
        """
        self.sendString(to_msgpack(msg))
        if loseConnection:
            self.transport.loseConnection()


class DHTFactory(protocol.Factory):
    """
    DHT Factory class that uses the DHTProtocol.
    """

    protocol = DHTProtocol

    def __init__(self, node):
        """
        Instantiates the factory with a node object representing the local
        node within the network.
        """
        self.node = node
