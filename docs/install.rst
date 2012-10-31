Installation Requirements
+++++++++++++++++++++++++

Use ``pip``
===========

To install the project either use a tool such as pip to download the latest
version from PyPI::

    $ pip install -U drogulus

Get the Code
============

Or clone/download the source code and run the following command::

    $ python setup.py install

If required, you can install the requirements with the following command::

    $ pip install -r requirements.txt

Requirements
============

Drogulus currently only relies upon PyCrypto, Twisted and MessagePack. Please
see these project's websites for more information:

* https://www.dlitz.net/software/pycrypto/
* http://twistedmatrix.com/
* http://msgpack.org/

Testing
=======

To run the test suite ensure you have the requirements installed and type::

    $ trial tests
