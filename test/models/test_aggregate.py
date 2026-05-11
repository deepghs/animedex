"""Tests for aggregate result models."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestAggregateResult:
    def test_source_status_helpers(self):
        from animedex.models.aggregate import AggregateResult, AggregateSourceStatus

        result = AggregateResult(
            items=[{"id": 1, "_source": "anilist"}],
            sources={
                "anilist": AggregateSourceStatus(status="ok", items=1),
                "jikan": AggregateSourceStatus(status="failed", reason="upstream-error", message="jikan 503"),
            },
        )

        assert set(result.ok_sources()) == {"anilist"}
        assert set(result.failed_sources()) == {"jikan"}
        assert result.all_failed is False

    def test_all_failed(self):
        from animedex.models.aggregate import AggregateResult, AggregateSourceStatus

        result = AggregateResult(
            items=[],
            sources={"anilist": AggregateSourceStatus(status="failed", reason="upstream-error")},
        )

        assert result.all_failed is True

    def test_default_containers_are_not_shared(self):
        from animedex.models.aggregate import AggregateResult

        first = AggregateResult()
        second = AggregateResult()

        assert first.items is not second.items
        assert first.sources is not second.sources

    def test_selftest_runs(self):
        from animedex.models import aggregate

        assert aggregate.selftest() is True
