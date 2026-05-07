Installation
============

.. note::
   ``animedex`` will be published to PyPI once it clears the v0.1.0
   milestone described in ``plans/04-roadmap-and-mvp.md``. Until then
   only an editable install from a clone is supported.

From source (development)
-------------------------

.. code-block:: bash

   git clone https://github.com/deepghs/animedex.git
   cd animedex
   pip install -e .

This installs the ``animedex`` console script and lets you exercise
the current scaffold:

.. code-block:: bash

   $ animedex --version
   animedex, version 0.0.1
   $ animedex status
   animedex v0.0.1 - work in progress.
   No backends are wired up yet. See plans/ in the repository.

Optional dependency groups
--------------------------

The repository ships several ``requirements-*.txt`` files. They are
also exposed as setuptools extras:

.. code-block:: bash

   pip install -e .[test]    # pytest, coverage, flake8, mock, ...
   pip install -e .[doc]     # sphinx + sphinx_rtd_theme + extensions

Supported Python versions
-------------------------

animedex targets Python 3.7 and newer. The CI matrix is currently
3.8 through 3.13 on Linux, Windows, and macOS; older versions may
still work but are not gated.

From PyPI (future)
------------------

Once published, the standard install will be:

.. code-block:: bash

   pip install animedex

Until then, the command above will return an HTTP 404 from PyPI.
