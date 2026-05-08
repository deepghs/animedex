"""High-level Waifu.im Python API.

Three thin wrappers over the JSON read endpoints on
``api.waifu.im``: :func:`tags`, :func:`images`, :func:`artists`.

NSFW posture mirrors the upstream: the ``/images`` endpoint defaults
to SFW only when ``isNsfw`` is omitted; pass ``is_nsfw=True`` from
Python (``--is-nsfw true`` from the CLI) to opt in to NSFW results.
The flag is a transparent passthrough to the upstream's ``isNsfw``
query parameter, not a paternalistic confirmation gate.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import waifu as _raw_waifu
from animedex.backends.waifu.models import WaifuArtist, WaifuImage, WaifuStats, WaifuTag
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="waifu",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a Waifu.im GET, parse the body, validate the envelope.

    :return: ``(parsed_payload_dict, source_tag)``.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` for non-text or
                       non-JSON bodies.
    """
    raw = _raw_waifu.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="waifu",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - waifu returns JSON
        raise ApiError("waifu returned a non-text body", backend="waifu", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"waifu 404 on {path}", backend="waifu", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"waifu {raw.status} on {path}", backend="waifu", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(f"waifu returned non-JSON body: {exc}", backend="waifu", reason="upstream-decode") from exc
    return payload, _src(raw)


def _items(payload: dict) -> List[dict]:
    """Pull the ``items`` list out of a paginated envelope."""
    if not isinstance(payload, dict) or "items" not in payload:
        raise ApiError("waifu response missing 'items' key", backend="waifu", reason="upstream-shape")
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ApiError("waifu 'items' is not a list", backend="waifu", reason="upstream-shape")
    return items


# ---------- /tags ----------


def tags(*, page_size: Optional[int] = None, config: Optional[Config] = None, **kw) -> List[WaifuTag]:
    """List every tag via ``/tags``.

    Each tag carries a ``name`` / ``slug`` / ``description`` plus
    its ``imageCount`` so callers can rank tags by popularity. The
    upstream wraps the response in a paginated envelope; the
    high-level helper returns just the ``items`` list.

    :param page_size: Optional ``pageSize`` override. ``None`` lets
                       the upstream default apply (currently 30).
    :type page_size: int or None
    :return: List of typed tags.
    :rtype: list[WaifuTag]
    """
    params: Dict[str, Any] = {}
    if page_size is not None:
        params["pageSize"] = page_size
    payload, src = _fetch("/tags", params=params, config=config, **kw)
    return [WaifuTag.model_validate({**row, "source_tag": src}) for row in _items(payload)]


# ---------- /artists ----------


def artists(
    *,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[WaifuArtist]:
    """List every artist via ``/artists``.

    :param page_number: 1-indexed page number; ``None`` returns
                         page 1 (the upstream default).
    :type page_number: int or None
    :param page_size: ``pageSize`` override.
    :type page_size: int or None
    :return: List of typed artists.
    :rtype: list[WaifuArtist]
    """
    params: Dict[str, Any] = {}
    if page_number is not None:
        params["pageNumber"] = page_number
    if page_size is not None:
        params["pageSize"] = page_size
    payload, src = _fetch("/artists", params=params, config=config, **kw)
    return [WaifuArtist.model_validate({**row, "source_tag": src}) for row in _items(payload)]


# ---------- /images ----------


def images(
    *,
    included_tags: Optional[List[str]] = None,
    excluded_tags: Optional[List[str]] = None,
    is_nsfw: Optional[bool] = None,
    is_animated: Optional[bool] = None,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None,
    config: Optional[Config] = None,
    **kw,
) -> List[WaifuImage]:
    """List image records via ``/images`` with optional filters.

    NSFW posture: when ``is_nsfw`` is ``None`` (the default), the
    parameter is omitted from the request and the upstream's
    SFW-only default applies. When ``is_nsfw=True``, NSFW images
    are returned. When ``is_nsfw=False``, SFW images are returned
    explicitly. The flag is a transparent passthrough; the project's
    posture is to inform the user about the upstream's defaults,
    not to gate.

    :param included_tags: Tag slugs that **must** be present on
                           returned images (multiple → all-of).
    :type included_tags: list of str or None
    :param excluded_tags: Tag slugs that **must not** be present.
    :type excluded_tags: list of str or None
    :param is_nsfw: NSFW filter. ``None`` (default) honours the
                     upstream's SFW-only default; ``True`` → NSFW
                     only; ``False`` → SFW only (explicit).
    :type is_nsfw: bool or None
    :param is_animated: ``True`` → only animated assets; ``False``
                         → only static; ``None`` → no filter.
    :type is_animated: bool or None
    :param page_number: 1-indexed page number.
    :type page_number: int or None
    :param page_size: Rows per page.
    :type page_size: int or None
    :return: List of typed images.
    :rtype: list[WaifuImage]
    """
    params: Dict[str, Any] = {}
    if included_tags:
        params["included_tags"] = list(included_tags)
    if excluded_tags:
        params["excluded_tags"] = list(excluded_tags)
    if is_nsfw is not None:
        params["isNsfw"] = "true" if is_nsfw else "false"
    if is_animated is not None:
        params["isAnimated"] = "true" if is_animated else "false"
    if page_number is not None:
        params["pageNumber"] = page_number
    if page_size is not None:
        params["pageSize"] = page_size
    payload, src = _fetch("/images", params=params, config=config, **kw)
    return [WaifuImage.model_validate({**row, "source_tag": src}) for row in _items(payload)]


def tag(id: int, *, config: Optional[Config] = None, **kw) -> WaifuTag:
    """Fetch one tag by numeric ID via ``/tags/{id}``.

    :param id: Numeric Waifu.im tag ID.
    :type id: int
    :return: Typed tag.
    :rtype: WaifuTag
    """
    payload, src = _fetch(f"/tags/{id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /tags/{id} did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuTag.model_validate({**payload, "source_tag": src})


def tag_by_slug(slug: str, *, config: Optional[Config] = None, **kw) -> WaifuTag:
    """Fetch one tag by URL-safe slug via ``/tags/by-slug/{slug}``.

    :param slug: Lowercased tag slug (e.g. ``"waifu"``).
    :type slug: str
    :return: Typed tag.
    :rtype: WaifuTag
    """
    payload, src = _fetch(f"/tags/by-slug/{slug}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /tags/by-slug/{slug} did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuTag.model_validate({**payload, "source_tag": src})


def artist(id: int, *, config: Optional[Config] = None, **kw) -> WaifuArtist:
    """Fetch one artist by numeric ID via ``/artists/{id}``.

    :param id: Numeric Waifu.im artist ID.
    :type id: int
    :return: Typed artist.
    :rtype: WaifuArtist
    """
    payload, src = _fetch(f"/artists/{id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /artists/{id} did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuArtist.model_validate({**payload, "source_tag": src})


def artist_by_name(name: str, *, config: Optional[Config] = None, **kw) -> WaifuArtist:
    """Fetch one artist by display name via ``/artists/by-name/{name}``.

    The response is the same artist envelope as ``/artists/{id}`` but
    additionally includes the artist's ``images`` list.

    :param name: Artist display name (case-sensitive).
    :type name: str
    :return: Typed artist (with extra ``images`` field via
              ``extra='allow'``).
    :rtype: WaifuArtist
    """
    payload, src = _fetch(f"/artists/by-name/{name}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /artists/by-name/{name} did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuArtist.model_validate({**payload, "source_tag": src})


def image(id: int, *, config: Optional[Config] = None, **kw) -> WaifuImage:
    """Fetch one image by numeric ID via ``/images/{id}``.

    :param id: Numeric Waifu.im image ID.
    :type id: int
    :return: Typed image.
    :rtype: WaifuImage
    """
    payload, src = _fetch(f"/images/{id}", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /images/{id} did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuImage.model_validate({**payload, "source_tag": src})


def stats_public(*, config: Optional[Config] = None, **kw) -> WaifuStats:
    """Fetch the public statistics envelope via ``/stats/public``.

    Returns a small object summarising the catalogue size + lifetime
    request volume; useful as a cheap upstream-liveness probe.

    :return: Typed statistics envelope.
    :rtype: WaifuStats
    """
    payload, src = _fetch("/stats/public", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "waifu /stats/public did not return a single object",
            backend="waifu",
            reason="upstream-shape",
        )
    return WaifuStats.model_validate({**payload, "source_tag": src})


def selftest() -> bool:
    """Smoke-test the public Waifu.im Python API (signatures only,
    no network).

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [
        tags,
        tag,
        tag_by_slug,
        artists,
        artist,
        artist_by_name,
        images,
        image,
        stats_public,
    ]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
