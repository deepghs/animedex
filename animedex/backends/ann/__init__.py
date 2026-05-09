"""High-level ANN Encyclopedia Python API.

ANN exposes a small anonymous XML surface: ``api.xml`` for by-id and
substring search, and ``reports.xml`` for curated encyclopedia lists.
The high-level API parses XML into typed rich models while preserving
``<warning>`` rows as data rather than errors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from animedex.api import ann as _raw_ann
from animedex.backends.ann.models import (
    AnnAnimeResponse,
    AnnReport,
    AnnXmlNode,
    anime_response_from_root,
    report_from_root,
)
from animedex.config import Config
from animedex.models.common import ApiError, SourceTag
from animedex.render.xml import xml_text_to_dict


def _src(envelope) -> SourceTag:
    return SourceTag(
        backend="ann",
        fetched_at=datetime.now(timezone.utc),
        cached=envelope.cache.hit,
        rate_limited=envelope.timing.rate_limit_wait_ms > 0,
    )


def _fetch_xml(path: str, *, params: Optional[Dict[str, Any]] = None, config: Optional[Config] = None, **kw):
    """Issue an ANN GET and parse the XML body into an adapted root."""
    raw = _raw_ann.call(path=path, params=params, config=config, **kw)
    if raw.firewall_rejected is not None:  # pragma: no cover - defensive
        raise ApiError(
            raw.firewall_rejected.get("message", "request blocked"),
            backend="ann",
            reason=raw.firewall_rejected.get("reason", "firewall"),
        )
    if raw.body_text is None:
        raise ApiError("ann returned a non-text body", backend="ann", reason="upstream-decode")
    if raw.status == 404:
        raise ApiError(f"ann 404 on {path}", backend="ann", reason="not-found")
    if raw.status >= 500:
        raise ApiError(f"ann {raw.status} on {path}", backend="ann", reason="upstream-error")
    try:
        root = AnnXmlNode.from_adapter(xml_text_to_dict(raw.body_text))
    except ApiError as exc:
        if exc.backend is None:
            exc.backend = "ann"
        raise
    return root, _src(raw)


def show(anime_id: int, *, config: Optional[Config] = None, **kw) -> AnnAnimeResponse:
    """Fetch one ANN anime encyclopedia entry by ANN ID.

    A missing ID returns a response with ``warnings`` populated and
    ``anime=[]``; this mirrors ANN's 200-OK warning contract.
    """
    root, src = _fetch_xml("/api.xml", params={"anime": anime_id}, config=config, **kw)
    return anime_response_from_root(root, src)


def search(q: str, *, config: Optional[Config] = None, **kw) -> AnnAnimeResponse:
    """Search ANN anime entries by title substring."""
    root, src = _fetch_xml("/api.xml", params={"anime": f"~{q}"}, config=config, **kw)
    return anime_response_from_root(root, src)


def reports(
    id: int = 155,
    *,
    type: Optional[str] = "anime",
    nlist: int = 10,
    nskip: Optional[int] = None,
    search: Optional[str] = None,
    name: Optional[str] = None,
    licensed: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> AnnReport:
    """Fetch a curated ANN encyclopedia report by report ID."""
    params: Dict[str, Any] = {"id": id, "nlist": nlist}
    if type is not None:
        params["type"] = type
    if nskip is not None:
        params["nskip"] = nskip
    if search:
        params["search"] = search
    if name:
        params["name"] = name
    if licensed is not None:
        params["licensed"] = licensed
    root, src = _fetch_xml("/reports.xml", params=params, config=config, **kw)
    if root.tag != "report":
        raise ApiError("ann reports.xml did not return a report XML root", backend="ann", reason="upstream-shape")
    return report_from_root(root, src)


def selftest() -> bool:
    """Smoke-test the ANN high-level package without network access."""
    from animedex.backends.ann import models

    return models.selftest()
