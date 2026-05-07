animedex
========

.. image:: https://img.shields.io/badge/license-Apache--2.0-green.svg
   :alt: Apache-2.0 license
   :target: https://github.com/deepghs/animedex/blob/main/LICENSE

.. image:: https://img.shields.io/badge/status-WIP-orange.svg
   :alt: Work in progress

A read-only, multi-source, ``gh``-flavored command-line interface for
anime and manga metadata. ``animedex`` is also a first-class Python
library: ``import animedex`` exposes the same backends, the same
source-attributed dataclasses, and the same raw-passthrough API that
the ``animedex`` console script uses.

.. note::
   The project is currently a scaffold: the per-backend commands and
   the high-level Python API are still being implemented. The bits that
   are wired up today are the version banner, the ``selftest``
   diagnostic, and the documentation build itself.

What animedex aims to be
------------------------

A single command modelled on `gh <https://cli.github.com/>`_, plus a
matching Python package, that:

* Aggregates the public anime and manga APIs surveyed by the project.
* Is **read-only by project scope**. animedex does not implement
  ``add to list`` / ``set score`` / ``favourite`` / upload commands.
  The read-only choice keeps auth small and lets us promise that the
  CLI does not disturb your existing account state.
* Names the source of every datum it returns. Every field carries
  ``[src: anilist]`` / ``[src: jikan]`` / ``[src: kitsu]`` / etc., so
  there is never a "magic merged answer" - you always know which
  upstream supplied which fact.
* Provides a ``gh api``-style raw passthrough (``animedex api
  <backend>``) for endpoints not covered by a high-level command.
* Doubles as an importable Python library with the same surface, so
  downstream automation can call into it without spawning subprocesses.

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   api_doc/index

Project repository
------------------

* `Source on GitHub <https://github.com/deepghs/animedex>`_
* `Issue tracker <https://github.com/deepghs/animedex/issues>`_
* `CI runs <https://github.com/deepghs/animedex/actions>`_

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
