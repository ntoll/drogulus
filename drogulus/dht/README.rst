The ``dht`` Module
==================

Contains a simple implementation of the Kademlia distributed hash table based
upon the Entangled implementation.

* constants.py - defines constants used by the Kademlia DHT network.
* kbucket.py - defines the "k-buckets" used to track contacts in the network.
* contact.py - defines a contact (another node) on the network.
* datastore.py - contains basic data storage classes for storing k/v pairs.
* routingtable.py - defines the routing table abstraction that contains information about other nodes and their associated states on the DHT network.
