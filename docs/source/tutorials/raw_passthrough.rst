Raw passthrough — ``animedex api``
==================================

When a high-level command does not cover what you need, the
``animedex api <backend> <path>`` subcommand sends a raw request to
the upstream and returns the response **unparsed**. It is the
project's escape hatch — modelled on ``gh api`` — and it still
honours the project's transport contract: rate limiting, the
read-only firewall, the per-backend ``User-Agent`` injection, and
the local SQLite cache all apply, even on the passthrough path.

Eight backends have raw-passthrough subcommands:

* ``animedex api anilist '<graphql-query>'`` — POST to AniList.
* ``animedex api jikan <path>`` — GET against Jikan v4.
* ``animedex api kitsu <path>`` — GET against Kitsu.
* ``animedex api mangadex <path>`` — GET against MangaDex.
* ``animedex api trace <path>`` — GET (or POST /search) against
  Trace.moe.
* ``animedex api danbooru <path>`` — GET against Danbooru.
* ``animedex api shikimori <path>`` — GET (REST) or POST /api/graphql.
* ``animedex api ann <path>`` — GET against Anime News Network's
  encyclopedia XML.
* ``animedex api nekos <path>`` — GET against nekos.best v2.

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
   animedex api jikan /anime/52991 --jq '.data.title'
   # => "Sousou no Frieren"

   # Curl-style: status + headers + body
   animedex api jikan /anime/52991 -i

   # Headers only — useful for the rate-limit headers
   animedex api nekos /husbando -I

   # Full envelope: timing breakdown + cache provenance + redirect chain
   animedex api jikan /anime/52991 --debug --jq '{status, cache, timing}'
   # => {
   #      "status":  200,
   #      "cache":   { "hit": false, "ttl_seconds": 86400, ... },
   #      "timing":  { "total_ms": 142, "rate_limit_wait_ms": 0, ... }
   #    }

GraphQL via AniList
-------------------

AniList is the only backend whose passthrough takes a body, not a
path. ``animedex api anilist`` accepts the GraphQL query as the
positional argument:

.. code-block:: bash

   animedex api anilist 'query { Media(id: 154587) { title { romaji } } }' \
     --jq '.data.Media.title.romaji'
   # => "Sousou no Frieren"

For variables, use ``--variables '<json>'``.

Common flags
------------

* ``--header / -H "Name: Value"`` — add a request header (repeatable).
  When the user supplies a ``User-Agent`` via ``-H``, it overrides
  the project default verbatim — ``animedex`` does not silently
  re-inject its own UA.
* ``--rate {normal,slow}`` — voluntary slowdown; ``slow`` halves
  the rate-limit refill rate so the backend's bucket burns through
  more slowly during long batch pulls.
* ``--cache <ttl-seconds>`` — override the per-backend default TTL.
* ``--no-cache`` — skip cache lookup AND skip cache write for this
  call.
* ``--no-follow`` — do not auto-follow 3xx redirects.
* ``--debug-full-body`` — with ``--debug``, do not truncate the body
  at 64 KiB.

Read-only firewall
------------------

The dispatcher rejects requests that would mutate upstream state
**before** they leave the host. The rules are per-backend and
explicit:

================ ==================================================
AniList          ``GET`` allowed; ``POST /`` allowed (GraphQL).
Jikan            ``GET`` only.
Kitsu            ``GET`` only.
MangaDex         ``GET`` only.
Danbooru         ``GET`` only.
Shikimori        ``GET`` only; ``POST /api/graphql`` allowed.
ANN              ``GET`` only.
Trace.moe        ``GET`` allowed; ``POST /search`` allowed.
nekos.best       ``GET`` only.
================ ==================================================

A rejection raises ``ApiError(reason="read-only")`` with a message
that names the policy — not "405 Method Not Allowed" (the upstream
would have accepted the request, the project rejected it).

The :doc:`python_library` page covers the equivalent
``animedex.api.<backend>.call(...)`` surface in Python.
