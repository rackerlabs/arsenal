============
Contributing
============

Contributions are encouraged and welcome!

For any type of change, please follow this general workflow:

#. Open an issue in `Arsenal's Github issue tracker`_. Describe the issue and
   tag it accordingly. That is, if the issue is a bug, please tag the issue
   as a bug. If an issue already exists, skip this step.    
#. Clone Arsenal's repository locally. 
#. Create a topic branch for the changes you plan to make in regards to the
   issue you're working on: ``git checkout -b your_branch_name``
#. Make your changes.
#. Add appropriate unit-tests.  If your change addresses a bug, please 
   add a unit test that proves the bug is fixed by your change. For 
   enhancements, try to thoroughly test all cases the new code will face.
#. Make sure all unit tests pass. ``tox -epy27,pep8`` should exercise all
   unit-tests and check for pep8 related style issues.
#. Commit your changes to your local repository and 
   `reference the appropriate Github issue in your commit message`_, 
   if appropriate.
#. Push your topic branch: ``your_banch_name`` to Github.
#. Create a pull request using the ``your_branch_name`` branch.

At that point, a repository maintainer will need to review and approve the
pull-request. You may be asked to make additional changes to your pull-request
before it is merged. 

Please note that any contributions will fall under the `Apache 2.0 license`_
governing this project.

Thanks for contributing!

.. _Arsenal's Github issue tracker: https://github.com/rackerlabs/arsenal/issues
.. _reference the appropriate Github issue in your commit message: https://help.github.com/articles/closing-issues-via-commit-messages/
.. _Apache 2.0 license: https://github.com/rackerlabs/arsenal/blob/master/LICENSE
