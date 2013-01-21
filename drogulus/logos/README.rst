``drogulus.logos``
======================

Logos is a Lisp-like language for giving Drogulus instructions. It is:

* Simple
* Easy to read
* Easy to understand
* Easy to share
* Homoiconic (code is expressed as data)
* Functional (there are no side effects when calling a function)
* Distributed
* Paxos-like
* Provides useful core data structures

Core Concepts
-------------

All data is immutable.

Comments start with a ";" sign (like Lisp).

An atom can be any of the following::

    ; A name that evaluates to itself
    name
    123-a-name
    &*£%^anothERNamE!!!
    ; Strings of unicode characters
    "String"
    'String'
    ; Numbers, both integer or floating point
    12345
    1.2345
    ; Boolean
    true
    false
    ; Datetime - shorthand for a dictionary structure
    2012-08-19:23-50-22
    ; Geolocation - shorthand for a dictionary structure
    -longitude|latitude^elevation

There are two types of collection, both of which are iterable sequences::

    (lists 'of' 12345 true "atoms)
    {dictionary-like: 'objects', 12345: true}

S-expressions are built as lists::

    (def something 'a value')

Quote like in Lisp::

    `(def something 'a value')

Functions are created with lambda::

    (def func-name (lambda (a b c)(;some code)))
    ; shorthand macro
    (def func-name (a b c) as (; some code)))
    ; all functions are actually objects
    (def func-name {
        args: (a, b, c),
        docs: "A document string",
        test: (; some tests),
        lambda: (; some code)
    })

Reference lists like this::

    ... TBD

Reference dictionaries like this::

    ... TBD

Logos includes tail call optimization::

    ... TBD

Logos is homoiconic and provides Lisp-y macros::

    ... TBD

Logos comes with batteries included for manipulating data in Drogulus::

    ... TDB
    (set ...)
    (get ...)
    (who-is? ...)
    (where-is? ...)
    (alias ...)
    (run ... ...)
    (out ...)
    (err ...)
    (import ...)
