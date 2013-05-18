Drogulus
========

**NB: This is an unfinished work in progress and does not yet work.**

Check out the project's website for more details: http://drogul.us

Drogulus is a programmable peer-to-peer data store designed for simplicity,
security, openness and fun. It's also an exercise in practical philosophy.

It's influenced by ideas from Fluidinfo (an openly writable data store),
Kademlia (a distributed hash table), Lisp, public/private key cryptography with
a dash of Xanadu thrown in for inspiration. It is implemented in Python and
requires very few external dependencies.

Current status: the distributed hash table is almost finished. Crypto based
work is done. Lisp implementation is an (uncommitted) toy which requires
further work although the design is pretty much done.

If in doubt, please ask. :-)

Should you wish to contribute please make sure you read CONTRIBUTE file. By
making a contribution you are agreeing to the terms described therein.

Quick Start
-----------

* Clone the repository: ``git clone git://github.com/ntoll/drogulus.git``
* I suggest you create a virtualenv for development purposes (see: https://pypi.python.org/pypi/virtualenv).
* Make sure you have a clean virtualenv. Then, within the resulting ``drogulus`` directory, type ``pip install -r requirements.txt`` to install all the project's requirements. This may take some minutes since the packages need to be downloaded from the internet.
* Next, type ``make check`` to run various code quality checks and the test suite. You should see a bunch of green ``OK`` messages scroll past. If you see errors, just ask.
* To build the documentation locally type ``make docs``. As the script will tell you, the resulting docs (as HTML) can be found in ``drogulus/docs/_build/html/index.html``.
* A simple demo application is coming soon...
