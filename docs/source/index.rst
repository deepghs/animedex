animedex
========

.. image:: https://img.shields.io/badge/license-Apache--2.0-green.svg
   :alt: Apache-2.0 license
   :target: https://github.com/deepghs/animedex/blob/main/LICENSE

.. image:: https://img.shields.io/badge/status-WIP%20%28scaffold%20only%29-orange.svg
   :alt: Work in progress
   :target: https://github.com/deepghs/animedex/tree/main/plans

A read-only, multi-source, ``gh``-flavored command-line interface for
anime and manga metadata, designed for both humans and LLM agents.

.. note::
   The project is currently a scaffold. None of the per-backend
   commands are wired up yet. The point of this early scaffolding is
   to lock in the design under ``plans/`` and the documentation
   surface that humans and agents share.

Top rule: human agency
----------------------

The user has full choice. Whatever the consequences of that choice,
they are the user's. ``animedex``'s job is to inform and to warn -
never to gate, refuse, or override. See the design rationale in
`plan 02 of the staged plans
<https://github.com/deepghs/animedex/blob/main/plans/02-design-policy-as-docstring.md>`_.

What animedex aims to be
------------------------

A single command modelled on `gh <https://cli.github.com/>`_ that:

* Aggregates the public anime and manga APIs surveyed in
  ``plans/01-public-apis-anime-survey.md``.
* Is **read-only by project scope**. animedex does not implement
  ``add to list`` / ``set score`` / ``favourite`` / upload commands.
* Names the source of every datum it returns. Every field carries
  ``[src: anilist]`` / ``[src: jikan]`` / etc. There is no anonymous
  merged answer.
* Treats safety policy as documentation, not as flags. Humans get the
  raw tool; agents get usage guidance in every docstring.
* Provides a ``gh api``-style raw passthrough (``animedex api <backend>``)
  so anything not covered by a high-level command is one HTTP call away.

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
