# -*- coding: utf-8 -*-
"""
An over engineered way of setting the version. Based upon a simplification of
how Django (http://djangoproject.com/) does it. ;-)
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


#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
VERSION = (0, 0, 0, 'alpha', 0)


def get_version():
    """
    Returns a string representation of the version information of this project.
    """
    return '.'.join([str(i) for i in VERSION])
