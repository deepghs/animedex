"""High-level Danbooru Python API.

Eight commands wrapping the most-used anonymous read endpoints on
``danbooru.donmai.us``: search / post / artist / artist-search /
tag / pool / pool-search / count.

The Danbooru tag-DSL surface is rich (rating filters, score
comparators, ``order:`` sorting, exclusion via ``-tag``); the high-
level :func:`search` accepts the raw tag string verbatim and forwards
it to the upstream. The project's posture per the Human Agency
Principle: when the user did not explicitly ask for adult content,
LLM agents should prepend ``rating:g`` to the tag query themselves;
the CLI / library never injects a content filter on the user's
behalf.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import danbooru as _raw_danbooru
from animedex.backends.danbooru.models import (
    DanbooruArtist,
    DanbooruCount,
    DanbooruPool,
    DanbooruPost,
    DanbooruTag,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="danbooru",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Danbooru GET, parse the body, validate the envelope.

    :return: ``(parsed_payload, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` for non-text or
                       non-JSON bodies.
    """
    raw = _raw_danbooru.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="danbooru",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - danbooru returns JSON
        raise ApiError("danbooru returned a non-text body", backend="danbooru", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"danbooru 404 on {path}", backend="danbooru", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"danbooru {raw.status} on {path}", backend="danbooru", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(
            f"danbooru returned non-JSON body: {exc}",
            backend="danbooru",
            reason="upstream-decode",
        ) from exc
    return payload, _src(raw)


def _list(payload: Any) -> List[dict]:
    """Coerce a payload that should be a list-of-records into one,
    tolerating Danbooru's occasional single-row return."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    return [payload]


# ---------- /posts ----------


def search(
    tags: Optional[str] = None,
    *,
    limit: int = 20,
    page: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[DanbooruPost]:
    """Tag-DSL search via ``/posts.json``.

    :param tags: Space-separated tag query (the upstream's DSL).
                  ``rating:g``, ``order:score``, ``score:>100``,
                  ``-tag`` (exclusion) and ``user:<name>`` are all
                  honoured by the upstream. When ``None``, the
                  upstream returns the latest posts unfiltered.
    :type tags: str or None
    :param limit: Max rows per page.
    :type limit: int
    :param page: 1-indexed page number.
    :type page: int
    :return: List of typed posts.
    :rtype: list[DanbooruPost]
    """
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if tags:
        params["tags"] = tags
    payload, src = _fetch("/posts.json", params=params, config=config, **kw)
    return [DanbooruPost.model_validate({**row, "source_tag": src}) for row in _list(payload)]


def post(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruPost:
    """Fetch one post by its numeric Danbooru ID via
    ``/posts/{id}.json``.

    :param id: Danbooru post ID.
    :type id: int
    :return: Typed post.
    :rtype: DanbooruPost
    """
    payload, src = _fetch(f"/posts/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /posts/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruPost.model_validate({**payload, "source_tag": src})


# ---------- /artists ----------


def artist(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruArtist:
    """Fetch one artist by ID via ``/artists/{id}.json``.

    :param id: Danbooru artist ID.
    :type id: int
    :return: Typed artist.
    :rtype: DanbooruArtist
    """
    payload, src = _fetch(f"/artists/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /artists/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruArtist.model_validate({**payload, "source_tag": src})


def artist_search(name: str, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[DanbooruArtist]:
    """Search artists by name (substring match) via
    ``/artists.json?search[any_name_or_url_matches]=<name>``.

    :param name: Substring to match against name / alias / URL.
    :type name: str
    :param limit: Max rows per page.
    :type limit: int
    :return: List of typed artists.
    :rtype: list[DanbooruArtist]
    """
    params = {"search[any_name_or_url_matches]": name, "limit": limit}
    payload, src = _fetch("/artists.json", params=params, config=config, **kw)
    return [DanbooruArtist.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /tags ----------


def tag(name: str, *, limit: int = 20, config: Optional[Config] = None, **kw) -> List[DanbooruTag]:
    """Look up a tag by exact or prefix-match name via
    ``/tags.json?search[name_matches]=<name>``.

    Returns a list because the upstream's ``name_matches`` accepts
    wildcards (e.g. ``touhou*``); pass an exact name to get a
    single-element list.

    :param name: Tag name (or wildcard pattern).
    :type name: str
    :param limit: Max rows per page.
    :type limit: int
    :return: List of typed tags.
    :rtype: list[DanbooruTag]
    """
    params = {"search[name_matches]": name, "limit": limit}
    payload, src = _fetch("/tags.json", params=params, config=config, **kw)
    return [DanbooruTag.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /pools ----------


def pool(id: int, *, config: Optional[Config] = None, **kw) -> DanbooruPool:
    """Fetch one pool by ID via ``/pools/{id}.json``.

    :param id: Danbooru pool ID.
    :type id: int
    :return: Typed pool.
    :rtype: DanbooruPool
    """
    payload, src = _fetch(f"/pools/{id}.json", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /pools/{id}.json did not return a single object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruPool.model_validate({**payload, "source_tag": src})


def pool_search(
    name: Optional[str] = None,
    *,
    limit: int = 20,
    page: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[DanbooruPool]:
    """Search pools by name substring via
    ``/pools.json?search[name_matches]=<name>``.

    :param name: Pool name substring; ``None`` lists all pools.
    :type name: str or None
    :param limit: Max rows per page.
    :type limit: int
    :param page: 1-indexed page number.
    :type page: int
    :return: List of typed pools.
    :rtype: list[DanbooruPool]
    """
    params: Dict[str, Any] = {"limit": limit, "page": page}
    if name:
        params["search[name_matches]"] = name
    payload, src = _fetch("/pools.json", params=params, config=config, **kw)
    return [DanbooruPool.model_validate({**row, "source_tag": src}) for row in _list(payload)]


# ---------- /counts ----------


def count(tags: Optional[str] = None, *, config: Optional[Config] = None, **kw) -> DanbooruCount:
    """Count posts matching a tag query via
    ``/counts/posts.json?tags=<tags>``.

    :param tags: Space-separated tag query (same DSL as
                  :func:`search`); ``None`` counts the entire
                  catalogue.
    :type tags: str or None
    :return: Typed count envelope; access ``.total()`` for the int.
    :rtype: DanbooruCount
    """
    params: Dict[str, Any] = {}
    if tags:
        params["tags"] = tags
    payload, src = _fetch("/counts/posts.json", params=params, config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "danbooru /counts/posts.json did not return an object",
            backend="danbooru",
            reason="upstream-shape",
        )
    return DanbooruCount.model_validate({**payload, "source_tag": src})


def selftest() -> bool:
    """Smoke-test the public Danbooru Python API (signatures only,
    no network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [search, post, artist, artist_search, tag, pool, pool_search, count]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
