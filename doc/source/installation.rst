============
Installation
============

Currently, the best way to obtain Arsenal is to clone the repository from
Github::

    $ git clone https://github.com/rackerlabs/arsenal.git

To perform a local installation, navigate to the repository's root and run::

    $ pip install . 

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv arsenal
    $ pip install .

For a development installation::
    
    $ pip install -e .

Should provide Arsenal to the system, while allowing development changes to
your local repository to be reflected in the installed package.

Unforuntately, Arsenal is not yet available from PyPI. However, that should
change soon.
