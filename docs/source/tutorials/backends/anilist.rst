``animedex anilist``
====================

The AniList backend wraps the public GraphQL endpoint at
``https://graphql.anilist.co``. animedex ships **28 anonymous
commands** (full coverage of AniList's anonymous read surface) plus
**4 auth-required stubs** that surface a clean ``ApiError(reason=
"auth-required")`` until token storage lands.

* **Backend**: AniList GraphQL.
* **Rate limit**: 30 req/min anonymous (degraded from baseline 90/min;
  the ``Retry-After`` header is honoured by the transport).
* **Auth**: not required for anonymous endpoints; OAuth PIN flow lands
  with token storage (see the master plan in
  `issue #1 <https://github.com/deepghs/animedex/issues/1>`_).

The full subcommand list is visible via ``animedex anilist --help``;
this page focuses on the ones you will actually reach for first.

Core lookups
------------

``show <id>`` — fetch a Media (anime / manga) by its AniList ID:

.. code-block:: bash

   animedex anilist show 154587 --jq '{romaji: .title.romaji, year: .seasonYear, score: .averageScore}'
   # => {
   #      "romaji": "Sousou no Frieren",
   #      "year":   2023,
   #      "score":  90
   #    }

``search <query>`` — fuzzy search across the AniList Media catalogue:

.. code-block:: bash

   animedex anilist search "Frieren" --jq '.[].title.romaji'
   # => "Sousou no Frieren"
   # => "Frieren"

``character <id>`` / ``staff <id>`` / ``studio <id>`` — same shape,
different entity:

.. code-block:: bash

   animedex anilist character 11 --jq '.name.full'
   # => "Edward Elric"

   animedex anilist studio 11 --jq '.name'
   # => "Madhouse"

Listings
--------

``trending`` — the AniList "Trending" rail, evaluated server-side:

.. code-block:: bash

   animedex anilist trending --jq '.[0:3] | map(.title.romaji)'

``schedule [year] [season]`` — the seasonal grid (defaults to the
current season):

.. code-block:: bash

   animedex anilist schedule 2024 spring --jq '.[].title.romaji'

``user <name>`` — public profile data for an AniList username
(the user's anime list, manga list, and stats are anonymous-readable):

.. code-block:: bash

   animedex anilist user "Josh" --jq '.statistics.anime.count'

Long tail
---------

The AniList GraphQL surface includes a long list of read-only
subqueries — recommendations, threads, reviews, activities, follows,
and more. animedex ships every one of them as a Click subcommand.
Discover them via ``--help``:

.. code-block:: bash

   animedex anilist --help          # group help, lists every subcommand
   animedex anilist review --help   # per-subcommand help with examples

Each subcommand returns the AniList GraphQL response wrapped in a
typed rich dataclass (lossless, dump-back-to-upstream-shape per the
project's :ref:`AGENTS.md` lossless contract).

Auth-required stubs (deferred)
------------------------------

The four endpoints that need a viewer token are wired as stubs that
raise ``ApiError(reason="auth-required")``:

* ``animedex anilist viewer``
* ``animedex anilist notification``
* ``animedex anilist markdown <text>``
* ``animedex anilist ani-chart-user <name>``

This is intentional: the stubs let library callers and agents
discover the surface today and code against it; the underlying
GraphQL queries already work end-to-end via ``animedex api anilist
'<query>'`` once you have a token.

Gotchas
-------

* **Rate ceiling is real**: 30 req/min is the AniList-degraded
  ceiling, not a soft hint. Repeated polling without ``--no-cache``
  is the right pattern; the local SQLite cache absorbs duplicates.
* **The "average" in averageScore is upstream-computed**, not a
  consensus across backends. If you want both AniList's and Jikan's
  takes on the same show, run both and compare; ``[src: …]``
  attribution makes that auditable.
* **GraphQL errors come back as 200 with an ``errors`` array**.
  animedex translates them into ``ApiError(reason="graphql-error")``.

The :doc:`../python_library` page covers the same surface from
inside Python.
