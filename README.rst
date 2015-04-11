The Drogulus
============

**This is an unfinished work in progress!**

A small and simple peer-to-peer data store and an exercise in practical
philosophy.

It'll probably all come to nothing. ;-)

You can't do much with the drogulus at the moment although this should change
very soon.

This is free and unencumbered software released into the public domain. Please
read the UNLICENSE file for details.

Why?
++++

The following three blog posts from a couple of years ago explain what I'm up
to (you should read them in the order they are listed):

* **Politics, Programming, Data and the Drogulus** - http://ntoll.org/article/ppdd
* **Drogulus - Questions and Clarifications** - http://ntoll.org/article/drogulus-questions-and-clarifications
* **How to Build a Drogulus** - http://ntoll.org/article/build-a-drogulus

Developer Setup
+++++++++++++++

This project requires Python version 3.3 (or higher).

Make a new virtualenv (see:
http://virtualenvwrapper.readthedocs.org/en/latest/) using Python > 3.3::

    $ mkvirtualenv drogulus

Install the requirements::

    $ pip install -r requirements.txt

The ``make`` command is a useful starting point. If you type ``make check``
and see a passing test suite followed by a coverage report then you should be
set up all fine and dandy.
