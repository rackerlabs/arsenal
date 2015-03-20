===========================================
Arsenal -- The Ironic image caching service
===========================================

.. image:: https://travis-ci.org/rackerlabs/arsenal.svg?branch=master
    :target: https://travis-ci.org/rackerlabs/arsenal

About
--------
* Free software: Apache license

TODO
--------
- Talk to Ironic
- Handle placing an image on an unprovisioned node, and tagging the node in Ironic/Nova
- Handle pluggable scheduling/decisioning around (flavor, image, available nodes)
- Create a Nova scheduler/filter to prefer cached nodes over uncached ones
- Find a way to measure cache hits versus misses
- Pin requirements
- Documentation
