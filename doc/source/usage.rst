========
Usage
========

arsenal-director
----------------

Arsenal is invoked by running::

    arsenal-director

With various arguments. All of ``arsenal-director``'s supported arguments are
documented on the command line. Run::

    arsenal-director --help

To see them, and a brief explanation on each one.

A reasonable invocation for actual use looks something like::

    arsenal-director --config-file /etc/arsenal/arsenal.conf --log-file /car/log/arsenal/arsenal-director.log

Which would start ``arsenal-director``, and it would try to load the 
configuration file found at ``/etc/arsenal/arsenal.conf`` while logging to
``/var/log/arsenal/arsenal-director.log``.

``arsenal-director`` will periodically gather data using the configured 
:ref:`Scout` object, and issuing directives returned by the configured 
:ref:`Strategy` object. ``arsenal-director`` will continue in this way 
indefinitely, only stopping through program termination.

.. important::
    It's a good idea to set the :ref:`dry_run option<dry_run option>` to 
    ``True`` in order to prevent ``arsenal-director`` from issuing directives 
    until you are confident that all the configuration settings appear to be 
    correct, and the directives emitted by the configured Strategy are 
    consistent with expected behavior.
