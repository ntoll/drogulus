The ``dht`` Module
==================

Contains a simple implementation of the Kademlia distributed hash table (inspired by, but containing no code from, the Entangled implementation of Kademlia).

* constants.py - defines constants used by the Kademlia DHT network.
* contact.py - defines a contact (another node) on the network.
* datastore.py - contains basic data storage classes for storing k/v pairs.
* kbucket.py - defines the "k-buckets" used to track contacts in the network.
* messages.py - internal representations of messages and functions needed to validate them.
* net.py - contains the low level networking code needed for communication between nodes on the network.
* routingtable.py - defines the routing table abstraction that contains information about other nodes and their associated states on the DHT network.
