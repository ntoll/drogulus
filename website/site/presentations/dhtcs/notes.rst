Distributed Hash Tables ~ Concise and Simple
============================================

High Level View
---------------

I find distributed hash tables fascinating. I want to give you a sense of why
I think this. I don't have much time so this will be a very high-level view
of how they work. There are references at the end.

Hashtable = dict (in Python)
----------------------------

Also called an associative array. Keys identify values and allow users to
interact with the data stored in the hashtable.

Distributed
-----------

This simply means that the whole hash table is stored across many different
nodes in the network. Similar to how a whole encyclopedia is stored in many
volumes.

Decentralized
-------------

Furthermore, all nodes are equal in status. There is no single points of
failure (like the web).

DHT = P2P K/V
-------------

A summary of what a DHT is.

How does a DHT work?
--------------------

We'll cover each of these points over the coming minutes.

Hashing
-------

Seed values are turned in to short hashes. War and Peace is reduced to a hash
of just 40 characters (a very large hex number).

Nodes
-----

Peers in the P2P network. Imagine this circle / clock-face represents all the
nodes in a very small DHT.

IDs from Hashes
---------------

Actually, a node's position in the DHT is derived from the value of the hash
that is its ID.

Items
-----

Key is the seed to create a new hash. Items are stored at node's whose IDs are
"close" to the key's hash.

This is not a difficult concept: it's how we know where to find items in an
encyclopedia (they're stored in volumes whose alphabetical range encompasses
the item).

The Routing Table
-----------------

But how do nodes know about each other in the P2P network?

Tracked using a data structure called the routing table.

Every interaction identifies nodes elsewhere on the network.

The routing table is split in to buckets. Each bucket contains no more than
N nodes. Buckets are smaller closer to the local node's ID. The local node
"knows" more about its local area of the P2P network.

Measures are taken to take in to account nodes joining and leaving the network.

Recursive Lookup
----------------

The core interaction between peers on the network that facilitates get and set
functionality.

The search repeatedly asks peers for nodes they know closer to the target.

The search finished when no closer nodes are found.

GET() and SET()
---------------

Obviously, in order to know who to interact with nodes have to do recursive
lookups.

All lookups are asynchronous.

Find out more
-------------

Not as well known as perhaps they should be.
