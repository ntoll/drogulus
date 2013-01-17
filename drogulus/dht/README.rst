``drogulus.dht``
================

Contains a simple implementation of the Kademlia distributed hash table.

* contact.py - defines a contact (another node) on the network.
* datastore.py - contains basic data storage classes for storing k/v pairs.
* kbucket.py - defines the "k-buckets" used to track contacts in the network.
* node.py - defines the local node within the DHT network.
* routingtable.py - defines the routing table abstraction that contains information about other nodes and their associated states on the DHT network.
