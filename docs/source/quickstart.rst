Quickstart
==========

.. warning::
   This page is a placeholder. The CLI is in scaffolding state and the
   commands shown below either do not yet exist or are stubs that
   print a "work in progress" notice. Please refer to the staged
   plans under ``plans/`` for the intended end state.

The intended interaction model
------------------------------

animedex is structured like ``gh``: each upstream service is its own
command group, plus a small set of cross-source aggregate commands
and a raw passthrough.

.. code-block:: bash

   # search anime via AniList GraphQL
   animedex anilist search "Frieren"

   # fetch the anime entry from MyAnimeList via Jikan
   animedex jikan show 52991

   # legal streaming-link aggregation via Kitsu
   animedex kitsu streaming 47390

   # screenshot reverse search via trace.moe
   animedex trace screenshot.jpg

   # tag-DSL search on Danbooru (the user is in charge of the query)
   animedex danbooru search "touhou marisa rating:g order:score"

Aggregate commands (cross-source, source-attributed)
----------------------------------------------------

.. code-block:: bash

   animedex search "Frieren"
   animedex show "Frieren"
   animedex crossref anilist:154587
   animedex season 2026 spring
   animedex schedule --day mon

The ``gh api``-style raw passthrough
------------------------------------

When a high-level command does not cover what you need, fall back to:

.. code-block:: bash

   animedex api anilist 'query { Media(id: 154587) { title { romaji } } }'
   animedex api jikan /anime/52991
   animedex api mangadex '/manga/{id}/feed?translatedLanguage[]=en' --paginate
   animedex api danbooru '/posts.json?tags=touhou+rating:g+order:score'

The passthrough still applies authentication, rate limiting, and
caching; it does not parse or filter the response. Mutating HTTP
methods are rejected by the project-scope read-only constraint.

Output formats
--------------

.. code-block:: bash

   animedex anilist show 154587                   # human-friendly TTY render
   animedex anilist show 154587 | jq .             # piped: full JSON
   animedex anilist show 154587 --json title,score # JSON, only selected fields
   animedex anilist show 154587 --jq '.title.romaji'
   animedex anilist show 154587 --web              # open the AniList page

For the full canonical command tree and the design rationale, read
``plans/03-cli-architecture-gh-flavored.md`` in the repository.
