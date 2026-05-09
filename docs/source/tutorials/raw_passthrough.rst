Raw passthrough — ``animedex api``
==================================

When a high-level command does not cover what you need, the ``animedex api <backend> <path>`` subcommand sends a raw request to the upstream and returns the response **unparsed**. It is the project's escape hatch, modelled on ``gh api``, and it still honours the project's physical transport contracts: rate limiting, the per-backend ``User-Agent`` injection, the MangaDex ``Via``-header strip, cache eligibility for known reads, and debug redaction all apply, even on the passthrough path. Method and path choices are forwarded verbatim; the caller owns the upstream result.

Twelve backends have raw-passthrough subcommands:

* ``animedex api anilist '<graphql-query>'`` — POST to AniList.
* ``animedex api jikan <path>`` — defaults to GET against Jikan v4.
* ``animedex api kitsu <path>`` — defaults to GET against Kitsu.
* ``animedex api mangadex <path>`` — defaults to GET against MangaDex.
* ``animedex api trace <path>`` — defaults to GET (or POST /search) against
  Trace.moe.
* ``animedex api danbooru <path>`` — defaults to GET against Danbooru.
* ``animedex api shikimori <path>`` — defaults to GET (REST) or POST /api/graphql.
* ``animedex api ann <path>`` — defaults to GET against Anime News Network's
  encyclopedia XML.
* ``animedex api nekos <path>`` — defaults to GET against nekos.best v2.
* ``animedex api waifu <path>`` — defaults to GET against Waifu.im.
* ``animedex api ghibli <path>`` — defaults to GET against the live Studio Ghibli API.
* ``animedex api quote <path>`` — defaults to GET against AnimeChan.

Output modes (mutually exclusive)
---------------------------------

Mirroring ``gh api``:

================== ===========================================================
Flag               Meaning
================== ===========================================================
*(default)*        Response body only.
``-i / --include`` Status line + response headers + body.
``-I / --head``    Status line + response headers only (no body).
``--debug``        Full ``RawResponse`` envelope as indented JSON, including
                   the request snapshot (credentials redacted), redirect
                   chain, per-call timing breakdown, and cache provenance.
================== ===========================================================

Examples
--------

.. code-block:: bash

   # Plain body, default mode
   animedex api jikan /anime/52991
   # => {"data":{"mal_id":52991,"title":"Sousou no Frieren",...}}

   # Curl-style: status + headers + body
   animedex api jikan /anime/52991 -i

   # Headers only — useful for the rate-limit headers
   animedex api nekos /husbando -I

   # Full envelope: timing breakdown + cache provenance + redirect chain
   animedex api jikan /anime/52991 --debug
   # => {
   #      "status":  200,
   #      "cache":   { "hit": false, "ttl_seconds": 86400, ... },
   #      "timing":  { "total_ms": 142, "rate_limit_wait_ms": 0, ... }
   #    }

Method Selection
----------------

``--method`` / ``-X`` sets the HTTP method sent through the raw dispatcher. ``GET`` is the default for REST backends. AniList still defaults to ``POST`` because GraphQL reads use ``POST /``. Shikimori GraphQL defaults to ``POST /api/graphql`` when ``--graphql`` is present and no explicit method was supplied. Trace.moe defaults to ``POST /search`` when ``--input`` is present and no explicit method was supplied.

.. code-block:: bash

   animedex api jikan /anime/52991 --method GET
   # => {"data":{"mal_id":52991,...}}

   animedex api jikan /anime -X DELETE
   # sends DELETE /anime to Jikan; the upstream response is returned unparsed

The raw passthrough does not reject mutating-looking methods on the user's behalf. Use them only when you intentionally want the upstream to receive that method; upstream authentication, authorization, and error behaviour are returned as-is.

Fields
------

``--field`` / ``-f`` and ``--raw-field`` / ``-F`` add gh-style fields to a raw request. REST ``GET`` calls receive them as query parameters, GraphQL calls receive them as variables, and JSON ``POST`` calls receive them in the JSON body when the wrapper is assembling one. Repeated keys use last-write-wins semantics across both flags.

``-f`` coerces values in this order: integer, float, literal ``true`` / ``false``, then string. ``-F`` always keeps strings.

.. code-block:: bash

   animedex api jikan /anime -f q=Naruto -f limit=2
   # => {"pagination":{"last_visible_page":15,"has_next_page":true,...},"data":[...]}

   animedex api anilist 'query($id:Int){ Media(id:$id){ id title{romaji} } }' -f id=154587
   # => {"data":{"Media":{"id":154587,"title":{"romaji":"Sousou no Frieren"}}}}

   animedex api jikan /anime -f limit=2 -F limit=2
   # sends the string query value "2"

Pagination
----------

``--paginate`` loops over supported raw ``GET`` endpoints and returns one JSON document containing a flat ``items`` list plus pagination metadata. The default ceiling is ``--max-pages 10``; pass ``--max-items`` to cap the accumulated list. Cache lookup remains per page, so an aggregate can legitimately contain cached and fresh page responses in the same run.

.. code-block:: bash

   animedex api jikan /anime -f q=Naruto -f limit=2 --paginate --max-pages 3
   # => {"items":[...6 records...],"pagination":{"backend":"jikan","pages_fetched":3,"items_fetched":6,"terminated_by":"max-pages",...}}

   animedex api mangadex /manga -f title=Berserk -f limit=2 --paginate --max-items 5
   # => {"items":[...5 records...],"pagination":{"backend":"mangadex","pages_fetched":3,"items_fetched":5,"terminated_by":"max-items",...}}

Supported pagination strategies are Jikan ``page`` / ``limit`` with an upstream pagination envelope, MangaDex ``offset`` / ``limit`` with ``total``, Danbooru and Shikimori ``page`` / ``limit`` with short-page termination, and AnimeChan quote lists using ``page`` with five quotes per page.

GraphQL via AniList
-------------------

AniList is the only backend whose passthrough takes a body, not a
path. ``animedex api anilist`` accepts the GraphQL query as the
positional argument:

.. code-block:: bash

   animedex api anilist 'query { Media(id: 154587) { title { romaji } } }'
   # => {"data":{"Media":{"title":{"romaji":"Sousou no Frieren"}}}}

For variables, use ``--variables '<json>'``.

Common flags
------------

* ``--method / -X METHOD`` — choose the HTTP method for the raw request. The method is forwarded verbatim.
* ``--field / -f K=V`` — add a typed field. REST ``GET`` sends it as a query parameter; GraphQL sends it as a variable.
* ``--raw-field / -F K=V`` — add a string-only field. Use this when the upstream distinguishes ``"10"`` from ``10``.
* ``--paginate`` — auto-paginate supported ``GET`` endpoints; use ``--max-pages`` and ``--max-items`` to bound the loop.
* ``--header / -H "Name: Value"`` — add a request header (repeatable).
  When the user supplies a ``User-Agent`` via ``-H``, it overrides
  the project default verbatim — ``animedex`` does not silently
  re-inject its own UA.
* ``--rate {normal,slow}`` — voluntary slowdown; ``slow`` halves
  the rate-limit refill rate so the backend's bucket burns through
  more slowly during long batch pulls.
* ``--cache <ttl-seconds>`` — override the per-backend default TTL.
* ``--no-cache`` — skip cache lookup AND skip cache write for cache-eligible requests.
* ``--no-follow`` — do not auto-follow 3xx redirects.
* ``--debug-full-body`` — with ``--debug``, do not truncate the body
  at 64 KiB.

Method responsibility
---------------------

The raw dispatcher does not maintain a method firewall. It still applies transport realities that make requests function at all: upstream rate limits, default ``User-Agent`` injection unless the caller overrides it, credential redaction in debug envelopes, cache eligibility for known reads, and the MangaDex ``Via`` strip. It does not block ``POST``, ``PUT``, ``PATCH``, or ``DELETE`` based on project policy.

The :doc:`python_library` page covers the equivalent
``animedex.api.<backend>.call(...)`` surface in Python.
