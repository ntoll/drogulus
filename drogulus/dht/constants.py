"""
Defines constants used by the Kademlia DHT network. Where possible naming is
derived from the original Kademlia paper.

Copyright (C) 2012 Nicholas H.Tollervey.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Represents the degree of parallelism in network calls.
ALPHA = 3

# The maximum number of contacts stored in a k-bucket. Must be an even number.
K = 20

# The timeout for network operations in seconds.
RPC_TIMEOUT = 5

# The delay between iterations of node lookups in seconds.
ITERATIVE_LOOKUP_DELAY = RPC_TIMEOUT / 2

# How long to wait before an unused k-bucket is refreshed (in seconds).
REFRESH_TIMEOUT = 3600 # 1 hour

# How long to wait before a node replicates any data it stores (in seconds).
REPLICATE_INTERVAL = REFRESH_TIMEOUT

# How long to wait before a node checks whether any buckets need refreshing or
# data needs republishing (in seconds).
REFRESH_INTERVAL = REFRESH_TIMEOUT / 6 # Every 10 minutes.
