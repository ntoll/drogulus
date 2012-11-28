"""
Defines a contact (another node) on the network.
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
from utils import long_to_hex


class Contact(object):
    """
    Represents another known node on the network.
    """

    def __init__(self, id, address, port, version, last_seen=0):
        """
        Initialises the contact object with its unique id within the DHT, IP
        address, port, the Drogulus version the contact is running and a
        timestamp when the last connection was made with the contact (defaults
        to 0). The id, if passed in as a numeric value, will be converted into
        a hexadecimal string.
        """
        if isinstance(id, long) or isinstance(id, int):
            self.id = long_to_hex(id)
        else:
            self.id = id
        self.address = address
        self.port = port
        self.version = version
        self.last_seen = last_seen
        # failed_RPCs keeps track of the number of failed RPCs to this contact.
        # If this number reaches a threshold then it is evicted from the
        # kbucket and replaced with a contact that is more reliable.
        self.failed_RPCs = 0

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

    def __ne__(self, other):
        """
        Override != to work with a string representation of the contact's id.
        """
        return not self == other

    def __repr__(self):
        """
        Returns a tuple containing the id, ip address and port number for this
        contact.
        """
        return str((self.id, self.address, self.port, self.version))

    def __str__(self):
        """
        Override the string representation of the object to be something
        useful.
        """
        return self.__repr__()
