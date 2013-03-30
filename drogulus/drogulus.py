# -*- coding: utf-8 -*-
"""
Encapsulates a node in the Drogulus.
"""

# Copyright (C) 2012-2013 Nicholas H.Tollervey.
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
from dht import node


class Drogulus(node.Node):
    """
    Represents a node in the Drogulus distributed hash table. This is the
    class that should generally be instantiated.
    """

    def __init__(self, alias=None):
        if alias:
            self.alias = alias
        else:
            self.alias = {}

    def whois(self, public_key):
        """
        """
        return self.get(public_key, None)

    def get(self, peer, key):
        """
        """
        pass

    def store(self, key, value, meta=None, expires=None, spread=1):
        """
        """
        pass

    def run(self, key, *args):
        """
        """
        pass
