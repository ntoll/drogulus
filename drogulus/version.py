# -*- coding: utf-8 -*-
"""
An over engineered way of setting the version. Based upon a simplification of
how Django (http://djangoproject.com/) does it. ;-)
"""


#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
VERSION = (0, 0, 0, 'alpha', 0)


def get_version():
    """
    Returns a string representation of the version information of this project.
    """
    return '.'.join([str(i) for i in VERSION])
