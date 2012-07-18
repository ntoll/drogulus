"""
Defines a contact (another node) on the network.

Copyright (C) 2012 Nicholas H.Tollervey.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

class Contact(object):
    """
    Represents another known node on the network.

    Will eventually contain an RPC mechanism for communicating with the node.
    """

    def __init__(self, id, address, port, last_seen=0):
        """
        @param id - the contact's id within the DHT.
        @param address - the contact's IP address.
        @param port - the contact's port.
        @last_seen - the last time there was a connection with the contact.
        """
        self.id = id
        self.address = address
        self.port = port
        self.last_seen = last_seen
        # failedRPCs keeps track of the number of failed RPCs to this contact.
        # If this number reaches a threshold then it is evicted from the
        # kbucket and replaced with a contact that is more reliable.
        self.failedRPCs = 0

    def __eq__(self, other):
        """
        Override equals to work with a string representation of the contact's
        id.
        """
        if isinstance(other, Contact):
            return self.id == other.id
        elif isinstance(other, str):
            return self.id == other
        else:
            return False

    def __str__(self):
        """
        Override the string representation of the object to be something
        useful.
        """
        return '<%s.%s object; IP address: %s, port: %d>' % (
            self.__module__, self.__class__.__name__, self.address, self.port)

    def __getattr__(self, name):
        """
        Makes calling a method on a remote node simple.
        """
        pass
