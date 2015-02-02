===============================
Arsenal (onmetal-image-scheduler) 
===============================

Arsenal - The OnMetal image caching service 

.. image:: https://travis-ci.org/rackerlabs/arsenal.svg?branch=master
    :target: https://travis-ci.org/rackerlabs/arsenal

About
--------
* Free software: Apache license
* TODO - Documentation: http://docs.openstack.org/developer/onmetal-image-scheduler
* Source: http://git.openstack.org/cgit/rackerlabs/onmetal-image-scheduler
* TODO - Bugs: http://bugs.launchpad.net/onmetal-image-scheduler

TODO
--------
- Talk to Ironic
- Handle placing an image on an unprovisioned node, and tagging the node in Ironic/Nova
- Handle scheduling/decisioning around (flavor, image, available nodes)
- Create a Nova scheduler/filter to prefer cached nodes over uncached ones
- Find a way to measure cache hits versus misses
