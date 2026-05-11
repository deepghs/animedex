"""Tests for the aggregate fan-out helper."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestFanout:
    def test_collects_successes_and_failures_in_source_order(self):
        from animedex.agg._fanout import fanout
        from animedex.models.common import ApiError

        result = fanout(
            {
                "a": lambda: [{"_source": "a", "id": 1}],
                "b": lambda: (_ for _ in ()).throw(ApiError("backend b 503", backend="b", reason="upstream-error")),
                "c": lambda: [{"_source": "c", "id": 3}],
            },
            concurrent=False,
        )

        assert [item["_source"] for item in result.items] == ["a", "c"]
        assert list(result.sources) == ["a", "b", "c"]
        assert result.sources["a"].status == "ok"
        assert result.sources["b"].status == "failed"
        assert result.sources["b"].http_status == 503
        assert result.sources["b"].reason == "upstream-error"
        assert result.all_failed is False

    def test_all_failed_is_true_only_when_no_source_succeeds(self):
        from animedex.agg._fanout import fanout
        from animedex.models.common import ApiError

        result = fanout(
            {
                "a": lambda: (_ for _ in ()).throw(ApiError("a 503", backend="a", reason="upstream-error")),
                "b": lambda: (_ for _ in ()).throw(ApiError("b 503", backend="b", reason="upstream-error")),
            },
            concurrent=False,
        )

        assert result.items == []
        assert result.all_failed is True
        assert set(result.failed_sources()) == {"a", "b"}

    def test_source_allowlist_preserves_available_order(self):
        from animedex.agg._fanout import select_sources

        assert select_sources(["anilist", "jikan", "kitsu"], "kitsu,anilist") == ["anilist", "kitsu"]

    def test_source_allowlist_rejects_unknown_names(self):
        from animedex.agg._fanout import select_sources
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="unknown source") as excinfo:
            select_sources(["anilist", "jikan"], "anilist,nope")
        assert excinfo.value.reason == "bad-args"
