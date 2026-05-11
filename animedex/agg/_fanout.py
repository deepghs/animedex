"""Shared concurrent fan-out helper for aggregate commands."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from animedex.models.aggregate import AggregateResult, AggregateSourceStatus
from animedex.models.common import ApiError


SourceCallable = Callable[[], List[Any]]


def _http_status_from_message(message: str) -> Optional[int]:
    """Best-effort status extraction from backend ``ApiError`` text."""
    for token in message.replace("(", " ").replace(")", " ").split():
        if token.isdigit() and len(token) == 3:
            value = int(token)
            if 100 <= value <= 599:
                return value
    return None


def fanout(sources: Dict[str, SourceCallable], *, concurrent: bool = True) -> AggregateResult:
    """Run source callables and collect successes plus failures.

    :param sources: Source name to zero-argument callable returning
                    JSON-ready row dicts.
    :type sources: dict[str, Callable[[], list[dict]]]
    :param concurrent: Whether to run sources in parallel.
    :type concurrent: bool
    :return: Aggregate result envelope.
    :rtype: AggregateResult
    """
    if not sources:
        return AggregateResult(items=[], sources={})
    if not concurrent or len(sources) == 1:
        pairs = [_run_one(name, fn) for name, fn in sources.items()]
    else:
        pairs = []
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            future_map = {executor.submit(_run_one, name, fn): name for name, fn in sources.items()}
            for future in as_completed(future_map):
                pairs.append(future.result())
    items: List[dict] = []
    statuses: Dict[str, AggregateSourceStatus] = {}
    for name, rows, status in sorted(pairs, key=lambda item: list(sources).index(item[0])):
        items.extend(rows)
        statuses[name] = status
    return AggregateResult(items=items, sources=statuses)


def _run_one(name: str, fn: SourceCallable) -> Tuple[str, List[Any], AggregateSourceStatus]:
    start = time.perf_counter()
    try:
        rows = list(fn())
    except ApiError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        message = str(exc)
        return (
            name,
            [],
            AggregateSourceStatus(
                status="failed",
                items=0,
                reason=exc.reason or "upstream-error",
                message=message,
                http_status=_http_status_from_message(message),
                duration_ms=duration_ms,
            ),
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return (
            name,
            [],
            AggregateSourceStatus(
                status="failed",
                items=0,
                reason="upstream-error",
                message=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            ),
        )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return (
        name,
        rows,
        AggregateSourceStatus(status="ok", items=len(rows), duration_ms=duration_ms),
    )


def select_sources(available: Iterable[str], requested: Optional[str]) -> List[str]:
    """Resolve a comma-separated source allowlist.

    :param available: Allowed source names.
    :type available: iterable[str]
    :param requested: Comma-separated source list or ``None``.
    :type requested: str or None
    :return: Selected sources in available-source order.
    :rtype: list[str]
    :raises ApiError: When an unknown source is requested.
    """
    available_list = list(available)
    if requested is None or not requested.strip():
        return available_list
    wanted = [part.strip() for part in requested.split(",") if part.strip()]
    unknown = [name for name in wanted if name not in available_list]
    if unknown:
        raise ApiError(
            f"unknown source(s): {', '.join(unknown)}; supported sources: {', '.join(available_list)}",
            backend="aggregate",
            reason="bad-args",
        )
    return [name for name in available_list if name in wanted]


def selftest() -> bool:
    """Smoke-test success, failure, and source selection paths.

    :return: ``True`` on success.
    :rtype: bool
    """
    result = fanout(
        {
            "a": lambda: [{"_source": "a"}],
            "b": lambda: (_ for _ in ()).throw(ApiError("boom", backend="b", reason="upstream-error")),
        },
        concurrent=False,
    )
    assert len(result.items) == 1
    assert result.sources["a"].status == "ok"
    assert result.sources["b"].status == "failed"
    assert select_sources(["a", "b"], "b") == ["b"]
    return True
