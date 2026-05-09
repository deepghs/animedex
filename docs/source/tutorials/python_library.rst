Python library
==============

The CLI is a thin presentation layer over an installable Python
package. Every command in the CLI tree is one ``from
animedex.backends.<x> import <fn>`` away, with the same return type
that the JSON renderer would have emitted.

Layout
------

================================== =====================================
Module                             What it exposes
================================== =====================================
``animedex.api``                   Raw passthrough dispatcher and per-backend ``call(...)`` shims (``anilist``, ``jikan``, ``kitsu``, ``mangadex``, ``trace``, ``danbooru``, ``shikimori``, ``ann``, ``nekos``).
``animedex.backends.anilist``      High-level AniList Python API (``show``, ``search``, ``character``, ``staff``, ``studio``, ``schedule``, ``trending``, ``user``, …).
``animedex.backends.jikan``        High-level Jikan Python API (87 anonymous endpoints).
``animedex.backends.trace``        High-level Trace.moe Python API (``search``, ``quota``).
``animedex.backends.nekos``        High-level nekos.best Python API (``categories``, ``categories_full``, ``image``, ``search``).
``animedex.models``                Cross-source common types (``Anime``, ``Character``, ``Staff``, ``Studio``, ``ArtPost``, ``TraceHit``, ``TraceQuota``).
``animedex.config``                ``Config`` dataclass for project-wide defaults.
================================== =====================================

Basic usage
-----------

.. code-block:: python

   from animedex.backends import anilist, jikan, nekos, trace

   # AniList — rich models preserve upstream GraphQL field names
   # verbatim (lossless contract), so attribute access is camelCase.
   media = anilist.show(154587)
   print(media.title.romaji, media.seasonYear, media.averageScore)
   # Sousou no Frieren 2023 90

   # Jikan
   anime = jikan.show(52991)
   print(anime.title, anime.score)
   # Sousou no Frieren 9.31

   # nekos.best
   for img in nekos.image("husbando", amount=3):
       print(img.url, img.artist_name)

   # Trace.moe — search() takes raw_bytes (or image_url); returns
   # a list of common-shape TraceHit (flat fields, not the nested
   # rich shape).
   with open("scene.jpg", "rb") as fh:
       hits = trace.search(raw_bytes=fh.read(), anilist_info=True)
   for hit in hits:
       print(hit.episode, hit.start_at_seconds, hit.anilist_id)

Every public function accepts:

* its endpoint-specific positional/keyword arguments;
* a final ``**kw`` that forwards to the dispatcher
  (``no_cache=True``, ``cache_ttl=3600``, ``rate="slow"``,
  ``timeout_seconds=5.0``, ``user_agent="my-bot/1.0"``,
  ``follow_redirects=False``);
* an optional ``config: Config = None`` for project-wide defaults
  (see below).

Cross-source projection
-----------------------

Backend-specific rich types (``AnilistAnime``, ``JikanAnime``,
``NekosImage``, ``RawTraceHit``, …) carry the upstream payload
losslessly. Each implements ``to_common()`` to project onto the
cross-source common type:

.. code-block:: python

   from animedex.backends import anilist, jikan, nekos
   from animedex.models.anime import Anime
   from animedex.models.art import ArtPost

   a: Anime = anilist.show(154587).to_common()
   m: Anime = jikan.show(52991).to_common()
   # Both `a` and `m` are the same `Anime` shape; compare them freely.

   art: ArtPost = nekos.image("husbando")[0].to_common()
   # ArtPost.rating is always "g" for nekos records (SFW-only API).

The lossless contract is pinned by a fixture-driven test:
``model_validate(upstream_payload)`` followed by
``model_dump(by_alias=True, mode="json")`` produces a key set that
is a *superset* of the upstream's. So a downstream consumer who
needs the full upstream payload can ``model_dump`` the rich type
and get an exact replay.

Raw passthrough
---------------

The ``animedex.api`` package mirrors the ``animedex api ...`` CLI:

.. code-block:: python

   from animedex.api import jikan as jikan_raw

   env = jikan_raw.call(path="/anime/52991", no_cache=True)
   print(env.status, env.body_text[:120])

   # Headers + redirects + timing breakdown live on the envelope:
   print(env.timing.total_ms, env.cache.hit, env.redirects)

Each per-backend shim accepts the same flags as the CLI: ``headers``,
``params``, ``no_cache``, ``cache_ttl``, ``rate``,
``follow_redirects``, ``user_agent``, ``timeout_seconds``, plus
explicit hooks for dependency injection (``cache``, ``session``,
``rate_limit_registry``, ``config``).

The ``Config`` entry point
--------------------------

A single :class:`~animedex.config.Config` carries project-wide
defaults for every CLI flag. The CLI builds one from its parsed
flags; library callers can build their own and pass it once:

.. code-block:: python

   from animedex.backends import anilist
   from animedex.config import Config

   cfg = Config(
       cache_ttl_seconds=600,        # tighter cache than default
       no_cache=False,
       rate="slow",                   # halve rate-limit refill
       source_attribution=True,
       user_agent="my-bot/1.2 (admin@example.org)",
       timeout_seconds=10.0,
   )

   media = anilist.show(154587, config=cfg)

A bare ``Config()`` (no arguments) reproduces the CLI's unflagged
behaviour. Each public API function accepts ``config=cfg``; the
keyword arguments on the call (``no_cache=True``, etc.) take
precedence over the ``Config`` default for that one call.

Errors
------

Every error path raises :class:`~animedex.models.common.ApiError`
with a typed ``reason``. The full vocabulary lives in
``animedex.models.common.REASONS`` (a frozenset; a typo at
construction time raises ``ValueError`` so it never reaches the
caller). Examples:

* ``not-found`` — 404 from upstream.
* ``upstream-error`` — 5xx from upstream.
* ``upstream-decode`` — non-text or non-JSON body where one was
  expected.
* ``upstream-shape`` — JSON parsed but the expected key was missing.
* ``graphql-error`` — AniList's body had a non-empty ``errors`` list.
* ``unknown-backend`` — typo in the backend identifier.
* ``auth-required`` — endpoint needs a token; raised by the four
  AniList stubs until token storage lands.
* ``bad-args`` — caller-side: ``amount`` out of range, empty query,
  etc.
* ``jq-failed`` — invalid jq expression at compile or runtime.
* ``jq-missing`` — the bundled jq wheel could not be imported.

Catch ``ApiError`` and branch on ``reason`` rather than parsing the
message:

.. code-block:: python

   from animedex.backends import jikan
   from animedex.models.common import ApiError

   try:
       anime = jikan.show(99999)
   except ApiError as exc:
       if exc.reason == "not-found":
           print("MAL has no anime with that id")
       elif exc.reason == "upstream-error":
           print("Jikan or MAL is having a bad day; retry later")
       else:
           raise

Testing
-------

Tests against animedex are easy because the only legal mock seam is
HTTP transport. Use the `responses
<https://github.com/getsentry/responses>`_ library to intercept the
``requests`` adapter; the rest of the stack runs end-to-end:

.. code-block:: python

   import responses
   from animedex.backends import anilist

   @responses.activate
   def test_anilist_show():
       responses.add(
           responses.POST,
           "https://graphql.anilist.co/",
           json={"data": {"Media": {"id": 154587, "title": {"romaji": "Sousou no Frieren"}}}},
       )
       result = anilist.show(154587, no_cache=True)
       assert result.title.romaji == "Sousou no Frieren"

The :doc:`agent_guide` page covers the same surface as it appears to
LLM agents shelling out via ``animedex --agent-guide`` rather than
importing the package.
