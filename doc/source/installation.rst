============
Installation
============

Deployment
----------

The easiest way to install arsenal is through ``pip``. See pip's 
`documentation on installation`_ to obtain it.

To install arsenal, run the following command::

   $ pip install --pre arsenal-director 

Here, we're instructing ``pip`` to install a package, namely 
``arsenal-director``. ``arsenal-director`` is the package name for Arsenal in 
`Python's Package Index`_. The ``--pre`` option lets ``pip`` install 
pre-release versions of packages. 

Currently, Arsenal is in beta. Once beta testing is complete, a full release 
will be made and the ``--pre`` option can be dropped from the above example.

Development
-----------

To obtain Arsenal for development, you should clone it directly from Github::

    $ git clone https://github.com/rackerlabs/arsenal.git

For a development installation, navigate to the cloned repository's root
and run::
    
    $ pip install -e .

Should provide Arsenal to the system, while allowing development changes to
your local repository to be reflected in the installed package.

Or, if you have virtualenvwrapper installed, and would like to place Arsenal 
in a virtual Python environment::

    $ mkvirtualenv arsenal
    $ pip install -e .

Should do the trick.

.. _documentation on installation: https://pip.readthedocs.org/en/latest/installing.html
.. _Python's Package Index: https://pypi.python.org/pypi
