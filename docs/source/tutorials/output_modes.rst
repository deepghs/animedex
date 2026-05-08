Output modes
============

Every animedex command picks one of three rendering paths: TTY,
JSON, or filtered-JSON-via-jq. The path is chosen automatically at
invocation time; this page explains the rules and how to override
them.

The auto-switch
---------------

By default, animedex inspects ``sys.stdout`` at the start of each
command and:

* if stdout is a real terminal, picks the **TTY renderer** (multi-line
  human-readable, with ``[src: <backend>]`` markers);
* if stdout is anything else (pipe, file redirect, subprocess),
  picks the **JSON renderer** (single-line-or-indented JSON with
  ``_source`` annotations and a top-level ``_meta`` block).

This means ``animedex anilist show 154587`` looks pretty when typed
into a terminal, and parses cleanly when used as
``animedex anilist show 154587 | jq …`` from a script. No flag
needed.

Three flags override the auto-switch
------------------------------------

* ``--json`` — force JSON output even when stdout is a terminal.
* ``--jq <expression>`` — force JSON, then filter through the
  bundled jq wheel.
* ``--no-source`` (JSON only) — drop the ``_source`` annotations
  and the top-level ``_meta`` block so the output is the upstream
  payload as-is.

TTY renderer
------------

The TTY renderer uses one formatter per cross-source common type
(``Anime`` / ``Character`` / ``Staff`` / ``Studio`` / ``TraceHit`` /
``TraceQuota``). Backend-specific rich types (``AnilistAnime``,
``JikanAnime``, ``NekosImage``) call ``to_common()`` and recurse
through the common formatter, with a generic JSON-dump fallback for
shapes that have no common projection.

.. code-block:: bash

   animedex anilist show 154587
   #
   # Sousou no Frieren  [src: anilist]
   #   ID:        anilist:154587
   #   Format:    TV
   #   Status:    finished
   #   Episodes:  28
   #   Year:      2023
   #   Score:     90
   #   ...

The ``[src: anilist]`` marker on the title line is the project's
promise that the rendered block names its origin. Cross-source
output (e.g. piping ``animedex search`` results through ``--json``)
attaches the marker per row.

JSON renderer
-------------

``--json`` (or any pipe / redirect) emits the upstream payload plus
two animedex-specific decorations:

* ``_source`` — a per-record provenance tag with ``backend``,
  ``fetched_at``, ``cached``, and ``rate_limited`` flags.
* ``_meta`` — a top-level block listing
  ``sources_consulted`` and (for aggregated commands) any
  per-source merge notes.

.. code-block:: bash

   animedex anilist show 154587 --json --jq '_meta'
   # => {
   #      "sources_consulted": [
   #        {"backend": "anilist", "cached": false, "rate_limited": false}
   #      ]
   #    }

To strip the decorations and get the upstream payload as-is:

.. code-block:: bash

   animedex anilist show 154587 --json --no-source --jq 'keys'

``--jq <expression>``
---------------------

The bundled `jq <https://jqlang.github.io/jq/>`_ Python wheel runs
the expression over the rendered JSON. It is a runtime dependency
that ships with the package — no host ``jq`` binary is required, no
PATH lookup happens, and the behaviour is identical across
Linux / macOS / Windows.

.. code-block:: bash

   # Single-value extract
   animedex jikan show 52991 --jq '.data.title'
   # => "Sousou no Frieren"

   # Multi-key projection
   animedex anilist show 154587 --jq '{romaji: .title.romaji, score: .averageScore}'

   # List-comprehension projection
   animedex anilist trending --jq '.[:5] | map(.title.romaji)'

   # Multi-emit filter — one JSON value per output line
   animedex nekos categories --json --jq '.[]'

A bad expression raises ``ApiError(reason="jq-failed")``, which
animedex surfaces as a clean ``click.ClickException`` (typed prefix,
non-zero exit, no Python traceback).

Caching
-------

Successful 2xx responses are written to a local SQLite cache at
``~/.cache/animedex/cache.sqlite`` (path resolves via
``platformdirs``). Default TTLs:

================ ============
Kind             TTL
================ ============
Metadata         72 hours
List endpoints   24 hours
Schedule grids   1 hour
Offline dumps    30 days
================ ============

Override per call:

.. code-block:: bash

   # Bypass cache entirely (no read, no write)
   animedex anilist show 154587 --no-cache

   # Override the TTL for this one call
   animedex anilist trending --cache 600

The ``animedex selftest`` diagnostic exercises the cache write/read
round-trip on every invocation.

Rate limiting
-------------

Each backend has its own per-process token bucket. Defaults:

================== ============================
AniList            30 req / min anonymous (degraded)
Jikan              60 req / min, 3 req / sec
Kitsu              10 req / sec
MangaDex           5 req / sec
Danbooru           10 req / sec
Shikimori          5 req / sec
ANN                1 req / sec
Trace.moe          0.5 req / sec, concurrency 1
nekos.best         3 req / sec sustained, 10-token burst (under the 200 / min upstream cap)
================== ============================

Pass ``--rate slow`` to halve the refill rate for long batch pulls.

The :doc:`../python_library` page exposes the same flags as keyword
arguments on every public function, plus a ``Config`` entry point for
project-wide defaults.
