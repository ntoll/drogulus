How does Drogulus Work?
+++++++++++++++++++++++

The drogulus is a programmable peer-to-peer data store. It is designed to
promote the autonomy of its users.

What does this mean?

* Programmable: The drogulus can be used to run programs. Programming is the creation and curation of instructions that produce results. Both instructions and results may be stored as data within the drogulus.
* Peer-to-peer (P2P): Peers of equal status (computers running appropriate software) cooperate in a loose decentralised network for mutual benefit. Peer to peer is the antithesis of hierarchy (where some have elevated status and power over others as in the client/server model of the Web). Furthermore, the loose and decentralised organisation of computing resources make it very hard for third parties to control users. The drogulus is, in fact, many computers collaborating together over the internet.
* Data store: a place where knowledge is stored in its latent digital form as data. "Data" are simply values that convey meaningful information about something. Meaning is implied by the context and structure of the data. Structure is formed from the way data is represented. The drogulus is a data store because users can create, retrieve, update and delete data distributed across its many nodes.

What is autonomy (and why is it so important)?

When someone is autonomous they are self-directing, free to act of their own
accord and lack imposition from others. Autonomy also suggests intelligence
and awareness enough to be able to enjoy and make use of such freedom.
Furthermore, such intelligence entails decision making so people become
accountable for their actions. Autonomy is also the opposite of such
undesirable states as tyranny, slavery, ignorance and apathy.

I asked myself, how would software designed to promote autonomy function? I
started to hack and the drogulus was born.

The drogulus is built with three technical "pillars":

* A distributed hash table provides the P2P data store.
* A cryptographic layer ensures the provenance and ownsership of data.
* A simple programming language called Logos uses the available computing power of the network to compute results.

Each is described, in some detail, below:

Distributed Hash Tables
=======================

When I started thinking about the drogulus I asked myself, "what is the
simplest yet most convenient data structure that people may require?". I
came to the conclusion that it was the associative array (hash-table) a
dictionary-like structure that allows users to name data.

This is a fundamental aspect of computing because it's a foundation for
abstraction: naming a thing hides what it is or how it works, it is merely
"X". Being empowered to name things is a fundamental aspect autonomy. In
his work, "Pedagogy of the Oppressed", the philosopher Paulo Freire says, "to
exist, humanly, is to name the world, to change it". Naming things (i.e.
abstracting) is a way to make sense to the world. To be able to do so without
imposition is liberating (double plus good).

Once data is named in the hash table it may also be referenced. This is the
essential requirement for hypertext. It should be possible to extract data from
the hash table as easily as extracting data from the web (another thing that
may be thought of as a kind of associative array - URLs name web pages).

At a high level (and also not entirely accurate, but close enough for
illustrative purposes) a distributed hash table (DHT) works like a sort of
peer-to-peer dictionary: a unique key (the name) is used to identify a value
(the data). In a traditional dictionary, the key is a word and the value is its
definition. Being a data store, the distributed hash table allows users to
create, retrieve, update and delete their own keys and associated digital
values.

The hash table is distributed because it is split into the equivalent of the
many volumes of a traditional dictionary (where each volume covers a particular
part of the whole). Each person who ever uses the DHT has a copy of just
one volume with many copies of a volume being distributed to many different
users.

Users keep track of which of their friends on the network hold what volume.
Users interact with the distributed hash table by contacting the friend with
the correct volume for the desired item. If they don't know anyone with the
right volume they play a sort of six-degrees-of-separation game with their
friends until someone with the correct volume is found.

The drogulus's distributed hash table also shares an interesting property with
Bittorrent: the more popular an entry is the more widespread it becomes, thus
improving performance since popular items are easier to find.

Distributed hash tables are eventually consistent and interactions with them
are done in an asynchronous manner.

The drogulus's DHT is based upon but is not the same as the Kademlia
distributed hash table algorithm. The innovation the drogulus brings is that
keys and values are signed in such a way that their provenance can be proven
and content shown to be intact. Furthermore, users cannot interfere with each
other's items stored within the distributed hash table unless they have access
to the same private key.

Items are self contained and any that do not pass the cryptographic checks are
ignored. Nodes that attempt to propagate such values are blocked (punished /
ostracized) by their peers.

Key Space
---------

A hash function is an algorithm that takes some arbitrary input block of data
and turns it in to a fixed size output. Any change to the input data will
change the resulting output. The name of the hash function used by the
drogulus is SHA-512.

Keys (names) are SHA-512 based values computed from two values provided by the
entity storing the data: its public key and a meangingful name.

Every node in the DHT also has a unique id that is a SHA-512 value. However,
this is computed from the node's own public key (used to facilitate
communication with other nodes on the network via SSH).

Nodes store items whose keys are "close" to their ids (see the section on
lookups and distance, below, for how this works).

Routing Table
-------------

The routing table is the data structure a node uses to keep track of its peers
in the distributed hash table. It is a binary tree whose leaves are k-buckets.

A k-bucket lists contact information about other nodes in a particular region
of the key space. The k-bucket is ordered from oldest to youngest node in terms
of last connection time. None of the k-buckets overlap, but together they cover
the whole key space.

A k-bucket can not contain more than K contacts - where K is a system wide
replication parameter. K represents the number of nodes that are unlikely to
fail within an hour of each other - typically, this value is set to 20.

Contact information consists of each peer's unique SHA-512 id within the DHT,
its IP address, port, the drogulus version the peer is running, a timestamp
indicating when the last connection was made with the peer and a counter
tracking the number of failed calls made from the local node to the peer
represented by the contact.

When a node joins the network it starts with a routing table containing just a
single k-bucket covering the whole key space. The routing table grows and
changes dynamically as more peers are encountered or drop off the network.

When a new peer is encountered on the network the local node attempts to add it
to the appropriate k-bucket that covers the area in the key space that the
new peer's id falls in to. Initially this will be the original single k-bucket.
If that k-bucket is not full (i.e. there are less than K contacts in it
already) then the new peer's contact information is simply added.

If the k-bucket is full and its range includes the local node's ID then it is
replaced by two new k-buckets each covering half the key space of the original
(full) k-bucket. The contact information for peers originally held in the
replaced k-bucket is divided between the two new k-buckets so peers are found
in the correct new k-bucket. The new peer, whose insertion caused the split,
has its contact information inserted in to the appropriate new k-bucket.

If the k-bucket covering the new peer is full and does not include the local
node's id then its contact information is added to a replacement cache for the
full k-bucket. If a peer in a full k-bucket has some arbitrary number of
failed calls then it is removed from the k-bucket and the oldest member of the
replacement cache that is still contactable is added to the k-bucket to replace
it.

The routing-table is usually kept up-to-date by the normal network traffic
between the local node and its peers. However, to guard against the odd case
when network traffic has not refreshed all the k-buckets the local node will
automatically refresh a k-bucket after some arbitrary amount of time (usually
an hour) by picking a random ID within the range of the k-bucket and performing
a node lookup for that ID (lookups are described below).

The local routing table may be asked for the K nearest peers to a certain
SHA-512 id value. Sometimes it may return peers from different k-buckets if the
desired id value is close to the "border" between k-buckets.

For the sake of clarity, here's a worked out "toy" example of the machinations
of a routing table.

Imagine that the key space is only the numbers from 0 to 999, that K is 5 and
our node's id is 234. When it joins the network its routing table consists of a
single k-bucket containing an already known "seed" peer (let's say the peer's
id is 765). As the node interacts with the distributed hash table it adds
contact information for the new peers it encounters to the routing table: for
example, for nodes with the ids, 001, 123, 456 and 876.

So far, so simple.

Now, given this state, when the node encounters another new node (say, with the
id 567) the routing table's single exitsing k-bucket is full. At this point,
the original k-bucket is replaced by two k-buckets for the ranges 0-499 and
500-999. The first new k-bucket now contains the contact details for the peers
with ids of 001, 123 and 456 whereas the second k-bucket contains contact
details for peers 567, 765, and 876.

Let's imagine that time passes and two more peers have been subsequently added
to the first k-bucket (with ids 098 and 345). Next, another new peer within the
first k-bucket's range is encountered (node 343). But the first bucket is full.
Since the first k-bucket also covers the range containing the local node's id
(remember, it's 234), it may be split again.

Now we have three k-buckets: 0-254, 255-499 and 500-999. The first k-bucket
contains contact details for peers 001, 098 and 123, the second k-bucket
contains contact details for peers 343, 345 and 456 and the third k-bucket
remains as it was.

However, if the k-bucket covering the range 500-999 was full and a new peer
within its range was encountered then the new peer's contact details would have
to be added to the replacement cache for the k-bucket since the k-bucket does
not cover the range containing the local node's id.

If, for example, the local node unsuccessfully attempted to contact peer 765
more than some pre-defined number of times then peer 765 would be removed from
the k-bucket and replaced with a reliable contact from its replacement cache.
This is how the DHT routes around failured peers and remote network problems.

Finally, the routing table may be asked for the K nearest peers it knows of
that are close to some arbitrary point. Let's say we want to know who is
closest to 500. The result will be K (5) contacts expressed as an ordered list
from closest to furthest away: 456, 567, 345, 343, 765.

Lookups and Distance
--------------------

Every message between peers includes the SHA-512 node id of the sender. This
permits peers to learn of each other's existence.

As has been mentioned before, keys are also SHA-512 values. To work out what
nodes store a given key a notion of distance is required. This allows the DHT
to search for peers close to a target key and retrieve its associated value.
Nodes found to be closest to the target key are used to store the target
key/value item.

The DHT defines the distance between a node id and key as simply an integer
representation of their bitwise exclusive or (XOR). This is both a simple and
uniform measure of distance.

Given such a mechanism for measuring distance between keys and ids it is
possible to navigate the DHT to look up keys and peers given a target SHA-512
value.

A lookup is an asynchronous operation that either calls back with a valid
result or an "errback". It's also possible to define a timeout for the lookup
in the drogulus's implementation of the DHT.

The lookup operation can be used to either find the K closest nodes to a
particular target in the key space, in order to store a value in to the DHT, or
retrieve a value for a given key.

A lookup is both parallel (in that more than one request at a time can be made
to fulfil the lookup) and recursive (in that such parallel requests return
peers closer to the target that are re-used to request yet closer peers until
a suitable result is found).

The following values are used in the lookup implemented by the drogulus (some
of the names are derived from the original Kademlia paper):

* the target key for the lookup
* the message type (either FindNode or FindValue)
* the routing table of the local node
* an ordered shortlist containing nodes close to the target
* a set of nodes that have been contacted during the lookup
* the id of the node nearest to the target (encountered so far)
* a dictionary of currently pending requests
* ALPHA - the number of concurrent asynchronous calls allowed
* K - the number of closest nodes to return when complete
* LOOKUP_TIMEOUT - the default maximum duration for a lookup

Given these values the lookup proceeds with the following steps:

0. If "timeout" number of seconds elapse before the lookup is finished then
   cancel any pending requests and errback with an OutOfTime error. The
   "timeout" value can be overridden but defaults to LOOKUP_TIMEOUT seconds.

1. Nodes from the local routing table seed the shortlist.

2. The nearest node to the target in the shortlist is set as nearest node.

3. No more than ALPHA nearest nodes that are in the shortlist but have not been
   contacted are sent a message that is an instance of the message type. Each
   request is added to the pending request dictionary. The number of pending
   requests must never be more than ALPHA.

4. As each node is contacted it is added to the "contacted" set.

5. If a node doesn't reply or an error is encountered it is removed from
   the shortlist and pending requests dictionary. Start from step 3 again.

6. When a response to a request is returned successfully remove the request
   from the pending requests dictionary.

7. If the lookup is for a FindValue message and a suitable value is returned
   (see note at the end of these comments) cancel all the other pending calls
   in the pending requests dictionary and fire a callback with the returned
   value. If the value is invalid remove the node from the short list and start
   from step 3 again without cancelling the other pending calls.

8. If a list of closer nodes is returned by a peer add them to the short list
   and sort - making sure nodes in the "contacted" set are not mistakenly
   re-added to the shortlist.

9. If the nearest node in the newly sorted shortlist is closer to the target
   than the current nearest node then set the nearest node to be the new
   closer node and start from step 3 again.

10. If the nearest node remains unchanged DO NOT start a new call.

11. If there are no other requests in the pending requests dictionary then
    check that the K nearest nodes in the "contacted" set are all closer
    than the nearest node in the shortlist. If they are, and it's a FindNode
    based lookup then call back with the K nearest nodes in the "contacted"
    set. If the lookup is for a FindValue message, errback with a
    ValueNotFound error.

12. If there are still nearer nodes in the shortlist to some of those in the
    K nearest nodes in the "contacted" set then start from step 3 again
    (forcing the local node to contact the close nodes that have yet to be
    contacted).

Note on validating values: In the future there may be constraints added to the
FindValue query (such as only accepting values created after time T).

Caching, Persistence and "Uptodatedness"
----------------------------------------

Some items stored in the DHT will be more popular than others. It is possible
to spread the effort for serving popular items to nodes other than those that
originally stored the popular item. Furthermore, nodes join or leave the DHT at
any time. Items are persisted to new nodes and steps are taken to ensure there
is no loss of data. Finally, items may be updated so it is important that newer
versions replace older items.

The DHT achieves these objectives in the following way:

For caching purposes (to ensure the availability of popular items), once a
FindValue lookup for an item succeeds, the requesting node stores the item at
the closest node it observed to the target key that did not return the value.
In this way the number of nodes storing the popular item grows and the
distance from the target key to the most distant ids of nodes storing the
popular item grows (so lookups find the item sooner since it's spread over a
wider area of the key space that is close to the target key).

To guard against lost data and to ensure new nodes obtain items with keys close
to their ids nodes attempt to republish items every hour. This simply involves
storing the item at the k currently closest nodes to the item's key. To avoid
excessive network traffic a node will not persist the value if it has itself
had the value republished to it within the hourly cycle.

To avoid over caching and before persisting an item this hourly process checks
how close the item's key is to host node's own id and when the item was last
requested. If they find the item has not been requested within the hour and its
key is far away (some arbitrary distance that may change over time as the item
becomes more out of date) then the item is removed from the local node. If the
item is still "close enough" and within its expiry date then nodes within this
area of the key space will continue to store the item no matter what.

If the item is found to have exceeded its expiry date then all nodes, no matter
where they are in the key space, will delete the item.

Every item contains a creation date to ensure more recent items take precedence
over older versions that may be encountered in the network. If a node attempts
to republish an old version of an item to a node with a more up-to-date
version then the older version is replaced by the newer one and the
republication activity is immediately repeated with the new (up-to-date) value.

Asynchronous Communication
--------------------------

All interactions with the DHT are asynchronous in nature and identified via a
UUID used by all the nodes involved in the interaction. Locally, a deferred
(representing the interaction) is returned by the drogulus to the application
layer. At some unknown time in the future the deferred will either fire with
a result or an error (which may be a timeout if the interaction took too long).

Cryptographic Trust
===================

The drogulus uses cryptography in two ways:

* Communication between nodes is done via SSH.
* Items stored in the DHT are cryptographically signed to ensure provenance.

SSH
---

SSH (Secure SHell - see https://en.wikipedia.org/wiki/Secure_Shell) is the
application layer protocol used to facilitate communication between nodes in
the drogulus. It means that all communication between nodes is encrypted.

It is important to note that this doesn't mean that values stored in the
drogulus are encrypted. It is simply as if messages are sent in envelopes that
can't be opened by third parties. The content of the envelopes may still be
unencrypted. It is left to the user to manage the encryption of their data.

SSH uses public key cryptography. Each node's public key is hashed using
SHA-512 to produce its id within the distributed hash table. This ensures the
location of a node's id within the key space cannot be controlled (avoiding
the possibility of an entity flooding the network with nodes whose ids are
near a certain valuable key). It also means that the node's alleged id can be
verified by quickly hashing its public key (the node's public key is a
fundamental requirement for the node to take part in communication within the
network).

Signing Items
-------------

Items stored in the distributed hash table are designed to stand on their own
and be self-verifiable.

Each item encompassing a key/value pair stored in the distributed hash table
contains the following fields:

* value - the actual value to store.
* timestamp - a UNIX timestamp representing when the creator of the item thinks
  the item was created (so it's easy to discern the latest version).
* expires - a UNIX timestamp beyond which the creator of the item would like
  the item to expire, be ignored and deleted.
* name - a meaningful name given by the creator for the key.
* meta - a list of tuples containing key/value strings for creator defined
  metadata about the item.
* created_with - the version of the protocol the creator used to generate the
  item.
* public_key - the creator's public key.
* sig - a cryptographic signature generated using the creator's private key
  with the value, timestamp, expires, name, meta and created_with values.
* key - the SHA-512 value of the compound key (based upon the public_key and
  name fields) used as the actual key on the distributed hash table.

The public_key field is used to validate the sig value. If this is OK then the
compound SHA-512 key is checked using the obviously valid public_key and name
fields.

This ensures both the provenance of the data and that it hasn't been tampered
with. Any items that don't pass the cryptographic checks are ignored and nodes
that propagate them are punished by being blocked.

Logos
=====

Logos is a variant of Lisp. It is also the least mature part of the drogulus,
but this is likely to change very soon.

Logos is designed to be simple enough for a 10 year old to understand but
powerful enough to be of use to professional programmers.

Language Overview
-----------------

Numbers

Maths

Strings

Variables and data structures

Defining functions

Macros

Deferreds

Session pad (messages to the user, drawing and displaying)

User input

Distributed Computation
-----------------------

See viff.

Distributing jobs out to the network.

Protection and trust.

Levels of Abstraction
---------------------

Logos is just the AST to which other things can compile.

Autonomy
--------

Lisp is a language for writing languages. Homoiconicity is the key.
