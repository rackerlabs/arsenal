===========================================
Arsenal - The Ironic image caching service
===========================================

.. image:: https://travis-ci.org/rackerlabs/arsenal.svg?branch=master
    :target: https://travis-ci.org/rackerlabs/arsenal
    :alt: Build Status
    
.. image:: https://readthedocs.org/projects/arsenal/badge/?version=latest
    :target: https://readthedocs.org/projects/arsenal/?badge=latest
    :alt: Documentation Status

About
--------
A small, Openstack-y service designed to manage image caching to nodes in Ironic_, written in Python.

Pluggable data-gathering and cache management strategy means Arsenal can be repurposed to work with other services.

Features
--------
* Pluggable data gathering.
* Pluggable strategy/decisioning around caching images to nodes.
* Built-in objects which provide client caching and API call retries to: Ironic_, Nova_, and Glance_.

Documentation
-------------

Hosted HTML docs for Arsenal are available at http://arsenal.readthedocs.org/

You may also build a local copy of Arsenal's documentation by using Sphinx::

    $ sphinx-build $repo_root/docs/source $output_dir
    
Then you can read the local documentation by pointing a browser at ``$output_dir/index.html``

Roadmap
--------

See issues labeled 'enhancements_' on Arsenal's Github project issues_ page.

.. _issues: https://github.com/rackerlabs/arsenal/issues
.. _enhancements: https://github.com/rackerlabs/arsenal/labels/enhancement
.. _Ironic: https://github.com/openstack/ironic
.. _Nova: https://github.com/openstack/nova
.. _Glance: https://github.com/openstack/glance
