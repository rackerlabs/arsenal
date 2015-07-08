======
Design
======
The core of Arsenal's functionality consists of gathering data for input, 
through :ref:`Scout` objects, to send to Arsenal's caching :ref:`Strategy` 
objects, which produce directives, which in turn are currently fulfilled by 
:ref:`Scout` objects. 
      
Therefore, Scouts deal with the outside world, while Strategies
provide introspection on data provided by Scouts to direct image caching on
nodes in some meaningful way. The Scout and Strategy objects used by 
``arsenal-director`` can be changed through configuration options. 

Arsenal's design philosophy can be summed up as: 
"Provide a way to do something, but make it easy to change or swap out."

.. _Scout:

Scout
-----

The responsibility of Scouts are to gather data from various outside sources,
like Ironic_, Nova_, and Glance_, convert that data to a form suitable for 
Strategy object consumption, as well as issue directives to endpoints, 
such as Ironic_.

All of Arsenal's Scout objects are derived from an abstract base class called
Scout, which is defined in `scout.py`_. 

.. tip::
    If you are thinking about defining your own Scout object, reading 
    `scout.py`_ is a good place to start.

A couple of pre-made Scouts are currently included in Arsenal.

.. _DevStack Scout:

DevStack Scout
~~~~~~~~~~~~~~

This Scout is designed to be used with the DevStack_ project, which provides
a relatively easy way to setup an Openstack-based environment on a single 
machine, typically for testing purposes.

The DevStack Scout will communicate with Ironic_, Nova_, and Glance_ services, 
and filter for baremetal nodes. See `Ironic documentation`_ on how to 
configure virtual baremetal nodes for use with DevStack.

For more information see, devstack_scout.py_.

.. _OnMetal Scout:

OnMetal Scout
~~~~~~~~~~~~~

The OnMetal Scout is designed to work with Rackspace's `OnMetal product`_. 
While this specific Scout will probably not be directly useful to anyone 
outside of Rackspace, it can still be instructive to view a fully functional, 
concrete implementation of a Scout. 

For more information, see onmetal_scout.py_.

.. _Strategy:

Strategy
--------

A Strategy's role lies in consuming data provided by Scouts, and then emitting
directives to manage imaging caching on nodes. 

Currently, two directives are supported. The first is **CacheNode**. 
**CacheNode** instructs the endpoint to cache a specific image onto a 
specific node. The second is **EjectNode**, which instructs the endpoint to do 
whatever is necessary to put a previously cached node back into an 
uncached state.

.. tip::
    If you are thinking about defining your own Strategy object, reading 
    `strategy/base.py`_ is a good place to start.

.. _SimpleProportionalStrategy:

SimpleProportionalStrategy
~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, SimpleProportionalStrategy is the only Strategy shipping with 
Arsenal.

This object implements a fairly straight-forward strategy: For each available 
flavor of node, use a constant proportion of available nodes for caching.

SimpleProportionalStrategy randomly picks available, uncached nodes to cache.
The random selection is designed to level wear across nodes.

Image selection is handled by ``choose_weighted_images_force_distribution``
found in the ``arsenal.strategy.base`` module. This means 
SimpleProportionalStrategy will pick images by weights pulled from the 
``strategy.image_weights`` option. See the :ref:`image_weights` option section
for more details on how image weighting works in Arsenal.

See the :ref:`[simple_proportional_strategy] Section` for information on how to 
configure this Strategy.

.. _scout.py: https://github.com/rackerlabs/arsenal/blob/master/arsenal/director/scout.py
.. _Ironic documentation: http://docs.openstack.org/developer/ironic/dev/dev-quickstart.html#deploying-ironic-with-devstack
.. _Ironic: https://github.com/openstack/ironic
.. _Nova: https://github.com/openstack/nova
.. _Glance: https://github.com/openstack/glance
.. _OnMetal product: http://www.rackspace.com/cloud/servers/onmetal/
.. _strategy/base.py: https://github.com/rackerlabs/arsenal/blob/master/arsenal/strategy/base.py
.. _DevStack: http://docs.openstack.org/developer/devstack/ 
.. _onmetal_scout.py: https://github.com/rackerlabs/arsenal/blob/master/arsenal/director/onmetal_scout.py
.. _devstack_scout.py: https://github.com/rackerlabs/arsenal/blob/master/arsenal/director/devstack_scout.py
