===========================================
Arsenal - The Ironic image caching service
===========================================

.. image:: https://travis-ci.org/rackerlabs/arsenal.svg?branch=master
    :target: https://travis-ci.org/rackerlabs/arsenal

About
--------
A small Python, Openstack-y service designed to manage image caching to nodes in Ironic_.

Pluggable data-gathering and cache management strategy means Arsenal can be repurposed to work with other services.

Features
--------
* Pluggable data gathering.
* Pluggable strategy/decisioning around caching images to nodes.
* Built-in objects which provide client caching and API call retries to: Ironic_, Nova_, and Glance_.

TODO
--------

See issues in Github project.

.. _Ironic: https://github.com/openstack/ironic
.. _Nova: https://github.com/openstack/nova
.. _Glance: https://github.com/openstack/glance
