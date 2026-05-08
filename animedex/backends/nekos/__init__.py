"""High-level nekos.best v2 Python API.

Three thin wrappers over the v2 endpoints:

* :func:`categories` — list every available category name (sugar
  over ``GET /endpoints``).
* :func:`image` — fetch one or more random images / GIFs from a
  named category.
* :func:`search` — best-effort metadata search across all categories.

Every function accepts ``config`` and forwards transport-level
keyword arguments to the underlying passthrough call.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from animedex.api import nekos as _raw_nekos
from animedex.backends.nekos.models import NekosCategoryFormat, NekosImage
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag


# ---------- internals ----------


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="nekos",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue a nekos.best v2 GET, parse the body, validate the envelope.

    :return: ``(parsed_payload, source_tag)``. Payload type depends on
              the endpoint — ``/endpoints`` returns a ``dict``,
              ``/<category>`` and ``/search`` return a ``dict`` with a
              top-level ``results`` array.
    :raises ApiError: ``not-found`` for 404, ``upstream-error`` for
                       5xx, ``upstream-decode`` if body is non-text.
    """
    raw = _raw_nekos.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="nekos",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:  # pragma: no cover - nekos.best always returns text JSON
        raise ApiError("nekos.best returned a non-text body", backend="nekos", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"nekos.best 404 on {path}", backend="nekos", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"nekos.best {raw.status} on {path}", backend="nekos", reason="upstream-error")
    try:
        payload = _json.loads(raw.body_text)
    except ValueError as exc:
        raise ApiError(f"nekos.best returned non-JSON body: {exc}", backend="nekos", reason="upstream-decode") from exc
    return payload, _src(raw)


def _validate_amount(amount: int) -> None:
    if not isinstance(amount, int) or amount < 1 or amount > 20:
        raise ApiError(
            f"nekos.best amount must be an integer 1..20; got {amount!r}",
            backend="nekos",
            reason="bad-args",
        )


def _validate_type(type_: int) -> None:
    if type_ not in (1, 2):
        raise ApiError(
            f"nekos.best type must be 1 (image) or 2 (gif); got {type_!r}",
            backend="nekos",
            reason="bad-args",
        )


def _attach_source(rows: List[dict], src: SourceTag) -> List[NekosImage]:
    return [NekosImage.model_validate({**row, "source_tag": src}) for row in rows]


# ---------- /endpoints ----------


def categories(*, config: Optional[Config] = None, **kw) -> List[str]:
    """List every nekos.best v2 category name.

    Calls ``GET /endpoints`` and returns just the category names,
    alphabetically. The richer per-category format data is available
    via :func:`categories_full` for callers that want the asset
    format and filename range.

    :return: Alphabetised list of category names.
    :rtype: list[str]
    """
    payload, _ = _fetch("/endpoints", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "nekos.best /endpoints did not return a JSON object",
            backend="nekos",
            reason="upstream-shape",
        )
    return sorted(payload.keys())


def categories_full(*, config: Optional[Config] = None, **kw) -> Dict[str, NekosCategoryFormat]:
    """List every category along with its per-category format
    metadata.

    Calls ``GET /endpoints`` and validates each entry through
    :class:`~animedex.backends.nekos.models.NekosCategoryFormat` so
    downstream callers get typed access to ``format`` / ``min`` /
    ``max``.

    :return: Mapping from category name to format metadata.
    :rtype: dict[str, NekosCategoryFormat]
    """
    payload, _ = _fetch("/endpoints", config=config, **kw)
    if not isinstance(payload, dict):
        raise ApiError(
            "nekos.best /endpoints did not return a JSON object",
            backend="nekos",
            reason="upstream-shape",
        )
    return {name: NekosCategoryFormat.model_validate(entry) for name, entry in payload.items()}


# ---------- /<category> ----------


def image(category: str, *, amount: int = 1, config: Optional[Config] = None, **kw) -> List[NekosImage]:
    """Fetch one or more random images / GIFs from a category.

    Calls ``GET /<category>?amount=<N>``. The upstream's response
    body is ``{"results": [<NekosImage>, ...]}``; each row is
    validated through :class:`~animedex.backends.nekos.models.NekosImage`.

    :param category: Category name (e.g. ``"husbando"``, ``"neko"``,
                      ``"waifu"``). Must be one of those returned by
                      :func:`categories`.
    :type category: str
    :param amount: Number of images to return, ``1..20``. Defaults
                    to ``1``.
    :type amount: int
    :return: List of images. The list is always at least one entry
              long when the category is valid.
    :rtype: list[NekosImage]
    :raises ApiError: ``bad-args`` for ``amount`` out of range,
                       ``not-found`` when the category is unknown.
    """
    _validate_amount(amount)
    if not category or "/" in category:
        raise ApiError(
            f"nekos.best category must be a non-empty name; got {category!r}",
            backend="nekos",
            reason="bad-args",
        )
    payload, src = _fetch(f"/{category}", params={"amount": amount}, config=config, **kw)
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ApiError(
            "nekos.best /<category> response missing 'results' array",
            backend="nekos",
            reason="upstream-shape",
        )
    return _attach_source(rows, src)


# ---------- /search ----------


def search(
    query: str,
    *,
    type: int = 1,
    category: Optional[str] = None,
    amount: int = 1,
    config: Optional[Config] = None,
    **kw,
) -> List[NekosImage]:
    """Search nekos.best v2 by metadata.

    Calls ``GET /search?query=<query>&type=<type>&amount=<amount>``
    (plus optional ``&category=<name>``). The upstream matches
    ``query`` against ``anime_name`` / ``artist_name`` / ``source_url``
    fuzzily and always returns up to ``amount`` results — a query
    that nothing closely matches falls through to a near-random
    ranking rather than an empty list.

    :param query: Search phrase.
    :type query: str
    :param type: Asset type filter — ``1`` for images (default), ``2``
                  for GIFs.
    :type type: int
    :param category: Restrict the search to one category.
    :type category: str or None
    :param amount: Maximum number of results, ``1..20``. Defaults to
                    ``1``. The upstream returns exactly ``amount``
                    results in practice — there is no empty-result
                    signal for non-matching queries.
    :type amount: int
    :return: List of matching images.
    :rtype: list[NekosImage]
    :raises ApiError: ``bad-args`` for ``amount`` or ``type`` out of
                       range, ``upstream-shape`` for malformed
                       responses.
    """
    _validate_amount(amount)
    _validate_type(type)
    if not query:
        raise ApiError("nekos.best search query must be non-empty", backend="nekos", reason="bad-args")
    params: Dict[str, Any] = {"query": query, "type": type, "amount": amount}
    if category is not None:
        params["category"] = category
    payload, src = _fetch("/search", params=params, config=config, **kw)
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ApiError(
            "nekos.best /search response missing 'results' array",
            backend="nekos",
            reason="upstream-shape",
        )
    return _attach_source(rows, src)


def selftest() -> bool:
    """Smoke-test the public nekos.best Python API (signatures only).

    Confirms each public callable accepts a ``config`` keyword so the
    Click factory's keyword-injection pattern works, and that the
    callables list matches the documented surface.

    :return: ``True`` on success.
    :rtype: bool
    """
    import inspect

    public_callables = [categories, categories_full, image, search]
    for fn in public_callables:
        sig = inspect.signature(fn)
        assert "config" in sig.parameters, f"{fn.__name__} missing config kwarg"
    return True
