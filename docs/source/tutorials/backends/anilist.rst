``animedex anilist``
====================

The AniList backend wraps the public GraphQL endpoint at
``https://graphql.anilist.co``. animedex ships **28 anonymous
commands** (full coverage of AniList's anonymous read surface) plus
**4 auth-required stubs** that surface a clean
``ApiError(reason="auth-required")`` until token storage lands.

.. image:: /_static/gifs/anilist.gif
   :alt: animedex anilist demo — show, search, character, studio, trending
   :align: center

References
----------

================================ =====================================
Site                             https://anilist.co/
GraphQL endpoint                 https://graphql.anilist.co/
API documentation                https://docs.anilist.co/
GitBook mirror                   https://anilist.gitbook.io/anilist-apiv2-docs/
Live schema browser              https://anilist.co/graphiql
Python module                    :mod:`animedex.backends.anilist`
Rich models                      :mod:`animedex.backends.anilist.models`
================================ =====================================

* **Backend**: AniList GraphQL.
* **Rate limit**: 30 req/min anonymous (degraded from baseline
  90/min; the ``Retry-After`` header is honoured by the transport).
* **Auth**: not required for anonymous endpoints; OAuth PIN flow
  lands with token storage.

The full subcommand list is visible via ``animedex anilist --help``.
This page walks the ten most common ones in detail and tabulates
the rest.

Core lookups
------------

Lookup a Media by AniList ID — :func:`~animedex.backends.anilist.show`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist show 154587 --jq '{romaji: .title.romaji, year: .seasonYear, score: .averageScore}'
   # => {
   #      "romaji": "Sousou no Frieren",
   #      "year":   2023,
   #      "score":  90
   #    }

   animedex anilist show 154587 --jq '.format, .episodes, .duration'
   # => "TV"
   # => 28
   # => 24

Search Media by free-text query — :func:`~animedex.backends.anilist.search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist search "Frieren" --per-page 5 --jq '.[] | {id, romaji: .title.romaji}'
   # => {"id": 154587, "romaji": "Sousou no Frieren"}
   # => {"id": 159831, "romaji": "Frieren ..."}
   # ...

Character lookup — :func:`~animedex.backends.anilist.character`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist character 11 --jq '.name.full'
   # => "Edward Elric"

   animedex anilist character 11 --jq '{name: .name.full, age: .age, gender}'

Staff lookup — :func:`~animedex.backends.anilist.staff`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist staff 101572 --jq '{name: .name.full, primary_occupations: .primaryOccupations}'
   # => {
   #      "name": "Hiromu Arakawa",
   #      "primary_occupations": ["Mangaka"]
   #    }

Studio lookup — :func:`~animedex.backends.anilist.studio`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist studio 11 --jq '{name, animation: .isAnimationStudio, favourites}'
   # => {
   #      "name":      "Madhouse",
   #      "animation": true,
   #      "favourites": 12345
   #    }

Search auxiliary entities
-------------------------

Character search — :func:`~animedex.backends.anilist.character_search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist character-search "Frieren" --per-page 3 --jq '.[].name.full'
   # => "Frieren"
   # => "Frieren ..."
   # => "..."

Staff search — :func:`~animedex.backends.anilist.staff_search`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist staff-search "Miyazaki" --per-page 3 --jq '.[].name.full'

Listings
--------

Trending rail — :func:`~animedex.backends.anilist.trending`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The AniList "Trending" rail, evaluated server-side:

.. code-block:: bash

   animedex anilist trending --per-page 5 --jq '.[] | {romaji: .title.romaji, score: .averageScore}'

Seasonal grid — :func:`~animedex.backends.anilist.schedule`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   animedex anilist schedule 2024 SPRING --jq '.[].title.romaji'
   # => "Series A"
   # => "Series B"
   # ...

Public profile lookup — :func:`~animedex.backends.anilist.user`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The user's anime list, manga list, and stats are anonymous-readable:

.. code-block:: bash

   animedex anilist user "Josh" --jq '{name, anime_count: .statistics.anime.count}'

Endpoint summary
----------------

The 28 anonymous endpoints are grouped here. Every command on this
table accepts the same standard kwargs (``--no-cache`` /
``--cache N`` / ``--rate slow`` / ``--json`` / ``--jq <expr>``) and
returns a typed rich dataclass losslessly preserving the upstream
GraphQL payload.

Core entities (typed returns)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Python entry point
     - Returns
   * - ``show <id>``
     - :func:`animedex.backends.anilist.show`
     - :class:`~animedex.backends.anilist.models.AnilistAnime`
   * - ``search <q>``
     - :func:`animedex.backends.anilist.search`
     - ``list[AnilistAnime]``
   * - ``character <id>``
     - :func:`animedex.backends.anilist.character`
     - :class:`~animedex.backends.anilist.models.AnilistCharacter`
   * - ``character-search <q>``
     - :func:`animedex.backends.anilist.character_search`
     - ``list[AnilistCharacter]``
   * - ``staff <id>``
     - :func:`animedex.backends.anilist.staff`
     - :class:`~animedex.backends.anilist.models.AnilistStaff`
   * - ``staff-search <q>``
     - :func:`animedex.backends.anilist.staff_search`
     - ``list[AnilistStaff]``
   * - ``studio <id>``
     - :func:`animedex.backends.anilist.studio`
     - :class:`~animedex.backends.anilist.models.AnilistStudio`
   * - ``studio-search <q>``
     - :func:`animedex.backends.anilist.studio_search`
     - ``list[AnilistStudio]``
   * - ``user <name>``
     - :func:`animedex.backends.anilist.user`
     - :class:`~animedex.backends.anilist.models.AnilistUser`
   * - ``user-search <q>``
     - :func:`animedex.backends.anilist.user_search`
     - ``list[AnilistUser]``

Discovery rails
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Command
     - Python entry point
     - Notes
   * - ``trending``
     - :func:`animedex.backends.anilist.trending`
     - the front-page trending rail
   * - ``schedule [year] [season]``
     - :func:`animedex.backends.anilist.schedule`
     - the seasonal grid (defaults to current season)
   * - ``airing-schedule``
     - :func:`animedex.backends.anilist.airing_schedule`
     - episode-level airing schedule (timestamps)
   * - ``genre-collection``
     - :func:`animedex.backends.anilist.genre_collection`
     - every AniList genre name
   * - ``media-tag-collection``
     - :func:`animedex.backends.anilist.media_tag_collection`
     - full tag taxonomy with descriptions
   * - ``site-statistics``
     - :func:`animedex.backends.anilist.site_statistics`
     - AniList-wide aggregate stats
   * - ``external-link-source-collection``
     - :func:`animedex.backends.anilist.external_link_source_collection`
     - registered streaming/mention sources
   * - ``media-trend <id>``
     - :func:`animedex.backends.anilist.media_trend`
     - per-Media trending data points

Reviews / threads / activity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Python entry point
     - Notes
   * - ``review <media_id>``
     - :func:`animedex.backends.anilist.review`
     - reviews for one Media
   * - ``recommendation``
     - :func:`animedex.backends.anilist.recommendation`
     - site-wide recommendation pairs
   * - ``thread <q>``
     - :func:`animedex.backends.anilist.thread`
     - forum thread search
   * - ``thread-comment``
     - :func:`animedex.backends.anilist.thread_comment`
     - comments on a thread
   * - ``activity``
     - :func:`animedex.backends.anilist.activity`
     - public activity feed
   * - ``activity-reply``
     - :func:`animedex.backends.anilist.activity_reply`
     - replies on one activity

Social graph (public reads)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Command
     - Python entry point
     - Notes
   * - ``following <user_id>``
     - :func:`animedex.backends.anilist.following`
     - who a user follows
   * - ``follower <user_id>``
     - :func:`animedex.backends.anilist.follower`
     - who follows a user
   * - ``media-list-public``
     - :func:`animedex.backends.anilist.media_list_public`
     - a user's anime/manga list
   * - ``media-list-collection-public``
     - :func:`animedex.backends.anilist.media_list_collection_public`
     - a user's full list collection

Auth-required stubs (deferred)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The four endpoints that need a viewer token are wired as stubs that
raise ``ApiError(reason="auth-required")``. They let library callers
and agents discover the surface today and code against it; the
underlying GraphQL queries already work end-to-end via
``animedex api anilist '<query>'`` once you have a token.

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Python entry point
     - Status
   * - ``viewer``
     - :func:`animedex.backends.anilist.viewer`
     - raises ``auth-required`` until token storage lands
   * - ``notification``
     - :func:`animedex.backends.anilist.notification`
     - same
   * - ``markdown <text>``
     - :func:`animedex.backends.anilist.markdown`
     - same
   * - ``ani-chart-user <name>``
     - :func:`animedex.backends.anilist.ani_chart_user`
     - same

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
