"""Aggregate command result models.

The aggregate layer composes several high-level backends while keeping
the source attribution contract explicit. Successful rows live in
``items``; per-source status, including partial failures, lives in
``sources``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from animedex.models.common import AnimedexModel


class AggregateSourceStatus(AnimedexModel):
    """Status row for one source consulted by an aggregate command.

    :ivar status: ``"ok"`` or ``"failed"``.
    :vartype status: str
    :ivar items: Number of successful rows returned by this source.
    :vartype items: int
    :ivar reason: Typed failure reason when the source failed.
    :vartype reason: str or None
    :ivar message: Human-readable failure summary.
    :vartype message: str or None
    :ivar http_status: Upstream HTTP status when known.
    :vartype http_status: int or None
    :ivar duration_ms: Wall-clock duration spent on this source.
    :vartype duration_ms: int
    """

    status: str
    items: int = 0
    reason: Optional[str] = None
    message: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: int = 0


class AggregateResult(AnimedexModel):
    """Envelope returned by multi-source aggregate commands.

    :ivar items: Successful rows. Each row is a JSON-ready dict that
                 carries ``_source`` and, for entity rows,
                 ``_prefix_id``.
    :vartype items: list[dict]
    :ivar sources: Per-source status map.
    :vartype sources: dict[str, AggregateSourceStatus]
    """

    items: List[Any] = []
    sources: Dict[str, AggregateSourceStatus] = {}

    def failed_sources(self) -> Dict[str, AggregateSourceStatus]:
        """Return the subset of sources that failed.

        :return: Source-status map containing only failed rows.
        :rtype: dict[str, AggregateSourceStatus]
        """
        return {name: status for name, status in self.sources.items() if status.status == "failed"}

    def ok_sources(self) -> Dict[str, AggregateSourceStatus]:
        """Return the subset of sources that succeeded.

        :return: Source-status map containing only successful rows.
        :rtype: dict[str, AggregateSourceStatus]
        """
        return {name: status for name, status in self.sources.items() if status.status == "ok"}

    @property
    def all_failed(self) -> bool:
        """Whether every selected source failed.

        :return: ``True`` when at least one source was selected and
                 none succeeded.
        :rtype: bool
        """
        return bool(self.sources) and not self.ok_sources()


def selftest() -> bool:
    """Smoke-test aggregate model validation and helpers.

    :return: ``True`` on success.
    :rtype: bool
    """
    result = AggregateResult(
        items=[{"id": 1, "_source": "demo", "_prefix_id": "demo:1"}],
        sources={
            "demo": AggregateSourceStatus(status="ok", items=1, duration_ms=1),
            "bad": AggregateSourceStatus(status="failed", reason="upstream-error", message="bad", duration_ms=2),
        },
    )
    assert set(result.ok_sources()) == {"demo"}
    assert set(result.failed_sources()) == {"bad"}
    assert not result.all_failed
    AggregateResult.model_validate_json(result.model_dump_json())
    failed = AggregateResult(
        items=[],
        sources={"bad": AggregateSourceStatus(status="failed", reason="upstream-error")},
    )
    assert failed.all_failed
    return True
