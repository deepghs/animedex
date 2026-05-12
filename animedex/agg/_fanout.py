"""Shared concurrent fan-out helper for aggregate commands.

Callers provide named source callables. The helper runs them
independently, catches per-source failures, and returns a structured
:class:`~animedex.models.aggregate.AggregateResult` instead of
raising on the first failed backend.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from animedex.models.aggregate import AggregateResult, AggregateSourceStatus
from animedex.models.common import ApiError


@dataclass(frozen=True)
class FanoutSource:
    """One source participating in aggregate fan-out.

    :ivar name: Backend identifier.
    :vartype name: str
    :ivar call: Zero-argument callable that returns this source's rows.
    :vartype call: callable
    """

    name: str
    call: Callable[[], object]


_HTTP_STATUS_RE = re.compile(
    r"\b(?:"
    r"HTTP(?:[/ ]?[0-9.]+)?\s+"
    r"|status(?:\s+code)?\s*[:=]?\s*"
    r"|returned\s+"
    r"|response\s+"
    r"|AniList\s+|Jikan\s+|Kitsu\s+|MangaDex\s+|Shikimori\s+|Danbooru\s+|ANN\s+|Trace\.moe\s+"
    r")"
    r"([1-5][0-9]{2})\b",
    re.IGNORECASE,
)


def _duration_ms(t_start: float) -> float:
    return round((time.monotonic() - t_start) * 1000.0, 3)


def _normalise_items(value: object) -> List[object]:
    """Return a list of successful rows from a source return value."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        for key in ("items", "data"):
            rows = value.get(key)
            if isinstance(rows, list):
                return rows
            if isinstance(rows, tuple):
                return list(rows)
        raise ApiError(
            "aggregate source returned a dict without list-shaped items or data",
            backend="aggregate",
            reason="upstream-shape",
        )
    rows = getattr(value, "rows", None)
    if isinstance(rows, list):
        return rows
    raise ApiError(
        f"aggregate source returned unsupported shape: {type(value).__name__}",
        backend="aggregate",
        reason="upstream-shape",
    )


def _http_status_from_message(message: str) -> Optional[int]:
    match = _HTTP_STATUS_RE.search(message)
    if match is None:
        return None
    return int(match.group(1))


def _status_from_exception(name: str, exc: BaseException, duration_ms: float) -> AggregateSourceStatus:
    reason = "upstream-error"
    backend = name
    if isinstance(exc, ApiError):
        reason = exc.reason or reason
        backend = exc.backend or backend
        message = exc.message
    else:
        message = f"{type(exc).__name__}: {exc}"
    return AggregateSourceStatus(
        backend=backend,
        status="failed",
        items=0,
        reason=reason,
        message=message,
        http_status=_http_status_from_message(str(exc)),
        duration_ms=duration_ms,
    )


def _run_one(source: FanoutSource):
    t_start = time.monotonic()
    try:
        items = _normalise_items(source.call())
    except Exception as exc:
        return source.name, [], _status_from_exception(source.name, exc, _duration_ms(t_start))
    return (
        source.name,
        items,
        AggregateSourceStatus(
            backend=source.name,
            status="ok",
            items=len(items),
            duration_ms=_duration_ms(t_start),
        ),
    )


def run_fanout(sources: Sequence[FanoutSource], *, max_workers: Optional[int] = None) -> AggregateResult:
    """Run source calls and return one aggregate envelope.

    :param sources: Source call descriptors to run.
    :type sources: sequence of FanoutSource
    :param max_workers: Optional thread-pool size. ``None`` means one
                        worker per source.
    :type max_workers: int or None
    :return: Aggregate result with successful rows and per-source
             statuses.
    :rtype: AggregateResult
    """
    if not sources:
        return AggregateResult(items=[], sources={})
    workers = max_workers if max_workers is not None else len(sources)
    workers = max(1, min(workers, len(sources)))
    items_by_source: Dict[str, List[object]] = {}
    statuses: Dict[str, AggregateSourceStatus] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_run_one, source): source.name for source in sources}
        for future in as_completed(futures):
            name, source_items, status = future.result()
            statuses[name] = status
            items_by_source[name] = source_items
    items: List[object] = []
    for source in sources:
        items.extend(items_by_source.get(source.name, []))
    ordered_statuses = {source.name: statuses[source.name] for source in sources}
    return AggregateResult(items=items, sources=ordered_statuses)


def selftest() -> bool:
    """Smoke-test success, empty, and failed fan-out paths.

    :return: ``True`` on success.
    :rtype: bool
    """

    def _ok():
        return [1, 2]

    def _empty():
        return []

    def _fail():
        raise ApiError("upstream returned 500", backend="bad", reason="upstream-error")

    result = run_fanout(
        [
            FanoutSource("ok", _ok),
            FanoutSource("empty", _empty),
            FanoutSource("bad", _fail),
        ],
        max_workers=1,
    )
    assert result.sources["ok"].items == 2
    assert result.sources["empty"].status == "ok"
    assert result.sources["bad"].http_status == 500
    assert len(result.items) == 2
    return True
