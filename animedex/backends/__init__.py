"""High-level Python API for each anime/manga backend.

The high-level backend layer introduces this package: each subpackage exposes typed functions for every read-only endpoint the upstream offers. Where
the substrate (:mod:`animedex.api`) wraps raw HTTP, this layer
wraps **meaning**: a call to :func:`animedex.backends.anilist.show`
returns a :class:`~animedex.backends.anilist.models.AnilistAnime`,
not a :class:`~animedex.api._envelope.RawResponse`.

Sub-packages:

* :mod:`animedex.backends.anilist` — AniList GraphQL.
* :mod:`animedex.backends.ann` — ANN Encyclopedia XML.
* :mod:`animedex.backends.danbooru` — Danbooru tag-DSL REST.
* :mod:`animedex.backends.jikan` — Jikan REST (MyAnimeList scraper).
* :mod:`animedex.backends.kitsu` — Kitsu JSON:API.
* :mod:`animedex.backends.mangadex` — MangaDex REST.
* :mod:`animedex.backends.nekos` — nekos.best image / GIF REST.
* :mod:`animedex.backends.shikimori` — Shikimori REST catalogue.
* :mod:`animedex.backends.trace` — Trace.moe screenshot search.
* :mod:`animedex.backends.waifu` — Waifu.im image REST.

Per ``plans/05-python-api.md`` §0.4, each backend ships:

* A **rich** dataclass (``Anilist*``, ``Ann*``, ``Jikan*``, ``Shikimori*``, ``Trace*``) that retains the long-tail fields the upstream exposes.
* A ``to_common()`` method projecting onto the cross-source types in
  :mod:`animedex.models` (``Anime``, ``Character``, ``Staff``,
  ``Studio``, ``TraceHit``).

Single-backend commands return the rich type; cross-source aggregate
commands (future aggregate work+) consume the common projection.
"""
