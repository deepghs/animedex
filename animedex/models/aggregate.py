"""Shared result envelope for multi-source aggregate commands.

Aggregate commands such as ``animedex search``, ``animedex show``,
``animedex season``, and ``animedex schedule`` fan out to one or more
upstream backends and may receive a mix of successful rows and
per-source failures. This module provides the stable envelope shape
those commands return: ``items`` contains only rows from successful
sources, while ``sources`` records one status row per selected
backend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import Field

from animedex.models.common import AnimedexModel, SourceTag


class AggregateSourceStatus(AnimedexModel):
    """Status row for one backend inside an aggregate response.

    :ivar backend: Backend identifier, e.g. ``"anilist"``.
    :vartype backend: str
    :ivar status: ``"ok"`` for a successful source, ``"failed"`` for
                  a source that raised while the fan-out continued.
    :vartype status: str
    :ivar items: Number of successful rows contributed by this source.
    :vartype items: int
    :ivar reason: Stable error reason when the source failed.
    :vartype reason: str or None
    :ivar message: Human-readable source failure message.
    :vartype message: str or None
    :ivar http_status: HTTP status code when the failure exposed one.
    :vartype http_status: int or None
    :ivar duration_ms: Wall-clock time spent in this source call.
    :vartype duration_ms: float
    """

    backend: str
    status: str
    items: int = 0
    reason: Optional[str] = None
    message: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: float = 0.0

    @property
    def ok(self) -> bool:
        """Return whether this source succeeded.

        :return: ``True`` when :attr:`status` is ``"ok"``.
        :rtype: bool
        """
        return self.status == "ok"


class AggregateResult(AnimedexModel):
    """Envelope returned by multi-source aggregate commands.

    The ``items`` list preserves each backend's rich model. Failures
    are deliberately not injected into ``items``; they live only in
    ``sources`` so a caller iterating over successful records never
    has to special-case failure sentinels.

    :ivar items: Successful rows from every healthy source.
    :vartype items: list
    :ivar sources: Per-source status map.
    :vartype sources: dict[str, AggregateSourceStatus]
    """

    items: List[Any] = Field(default_factory=list)
    sources: Dict[str, AggregateSourceStatus] = Field(default_factory=dict)

    @property
    def failed_sources(self) -> Dict[str, AggregateSourceStatus]:
        """Return the failed source statuses.

        :return: Mapping containing only failed sources.
        :rtype: dict[str, AggregateSourceStatus]
        """
        return {name: status for name, status in self.sources.items() if not status.ok}

    @property
    def succeeded_count(self) -> int:
        """Return how many selected sources succeeded.

        :return: Number of ``status == "ok"`` entries.
        :rtype: int
        """
        return sum(1 for status in self.sources.values() if status.ok)

    @property
    def all_failed(self) -> bool:
        """Return whether every selected source failed.

        :return: ``True`` when at least one source was selected and
                 none succeeded.
        :rtype: bool
        """
        return bool(self.sources) and self.succeeded_count == 0


def selftest() -> bool:
    """Smoke-test the aggregate envelope model.

    The diagnostic runner invokes this to confirm that nested rich
    models can be carried through the aggregate JSON path and that the
    source-status helpers behave correctly.

    :return: ``True`` on success.
    :rtype: bool
    """
    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    result = AggregateResult(
        items=[src],
        sources={
            "ok": AggregateSourceStatus(backend="ok", status="ok", items=1),
            "failed": AggregateSourceStatus(
                backend="failed",
                status="failed",
                reason="upstream-error",
                message="failed",
                http_status=500,
            ),
        },
    )
    decoded = result.model_dump(mode="json")
    assert decoded["items"][0]["backend"] == "_selftest"
    assert result.succeeded_count == 1
    assert list(result.failed_sources) == ["failed"]
    assert not result.all_failed
    failed = AggregateResult(
        items=[],
        sources={"bad": AggregateSourceStatus(backend="bad", status="failed", reason="upstream-error")},
    )
    assert failed.all_failed
    return True
