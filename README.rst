===========================================
Arsenal - The Ironic image caching service
===========================================

.. image:: https://travis-ci.org/rackerlabs/arsenal.svg?branch=master
    :target: https://travis-ci.org/rackerlabs/arsenal

About
--------
A small, Openstack-y service designed to manage image caching to nodes in Ironic_, written in Python.

Pluggable data-gathering and cache management strategy means Arsenal can be repurposed to work with other services.

Features
--------
* Pluggable data gathering.
* Pluggable strategy/decisioning around caching images to nodes.
* Built-in objects which provide client caching and API call retries to: Ironic_, Nova_, and Glance_.

Roadmap
--------

See issues labeled 'enhancements_' on Arsenal's Github project issues_ page.

.. _issues: https://github.com/rackerlabs/arsenal/issues
.. _enhancements: https://github.com/rackerlabs/arsenal/labels/enhancement
.. _Ironic: https://github.com/openstack/ironic
.. _Nova: https://github.com/openstack/nova
.. _Glance: https://github.com/openstack/glance
