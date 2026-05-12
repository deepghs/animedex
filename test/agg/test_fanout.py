"""Unit tests for aggregate fan-out helper branches."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestFanoutBranches:
    def test_normalises_none_tuple_dict_and_rows_object(self):
        from animedex.agg._fanout import _normalise_items
        from animedex.models.common import ApiError

        class Rows:
            rows = [1, 2]

        assert _normalise_items(None) == []
        assert _normalise_items((1, 2)) == [1, 2]
        assert _normalise_items({"items": [3, 4]}) == [3, 4]
        assert _normalise_items({"data": (5, 6)}) == [5, 6]
        assert _normalise_items(Rows()) == [1, 2]
        with pytest.raises(ApiError) as err:
            _normalise_items({"meta": {"total": 2}})
        assert err.value.reason == "upstream-shape"
        with pytest.raises(ApiError) as err:
            _normalise_items("x")
        assert err.value.reason == "upstream-shape"
        assert "unsupported shape: str" in err.value.message

    def test_http_status_requires_status_context(self):
        from animedex.agg._fanout import _http_status_from_message

        assert _http_status_from_message("boom") is None
        assert _http_status_from_message("limit=200 reached") is None
        assert _http_status_from_message("per_page=400 rejected") is None
        assert _http_status_from_message("season 2024 spring") is None
        assert _http_status_from_message("mangadex auth returned 401: Invalid") == 401
        assert _http_status_from_message("HTTP 429 too many requests") == 429
        assert _http_status_from_message("HTTP/1.1 503 Service Unavailable") == 503
        assert _http_status_from_message("AniList 429") == 429
        assert _http_status_from_message("Jikan 404 on /v4/anime/99999999") == 404
        assert _http_status_from_message("status code=500") == 500
        assert _http_status_from_message("response 403 from upstream") == 403

    def test_plain_exception_becomes_failed_status(self):
        from animedex.agg._fanout import _status_from_exception

        status = _status_from_exception("jikan", RuntimeError("boom"), 1.0)
        assert status.backend == "jikan"
        assert status.reason == "upstream-error"
        assert "RuntimeError" in status.message

    def test_empty_source_list_returns_empty_result(self):
        from animedex.agg._fanout import run_fanout

        result = run_fanout([])
        assert result.items == []
        assert result.sources == {}
        assert result.all_failed is False

    def test_collects_successes_and_failures_in_source_order(self):
        from animedex.agg._fanout import FanoutSource, run_fanout
        from animedex.models.common import ApiError

        result = run_fanout(
            [
                FanoutSource("a", lambda: [{"_source": "a", "id": 1}]),
                FanoutSource(
                    "b",
                    lambda: (_ for _ in ()).throw(
                        ApiError("backend b returned 503", backend="b", reason="upstream-error")
                    ),
                ),
                FanoutSource("c", lambda: [{"_source": "c", "id": 3}]),
            ],
            max_workers=1,
        )

        assert [item["_source"] for item in result.items] == ["a", "c"]
        assert list(result.sources) == ["a", "b", "c"]
        assert result.sources["a"].backend == "a"
        assert result.sources["a"].status == "ok"
        assert result.sources["b"].status == "failed"
        assert result.sources["b"].http_status == 503
        assert result.sources["b"].reason == "upstream-error"
        assert result.all_failed is False

    def test_all_failed_is_true_only_when_no_source_succeeds(self):
        from animedex.agg._fanout import FanoutSource, run_fanout
        from animedex.models.common import ApiError

        result = run_fanout(
            [
                FanoutSource(
                    "a", lambda: (_ for _ in ()).throw(ApiError("a 503", backend="a", reason="upstream-error"))
                ),
                FanoutSource(
                    "b", lambda: (_ for _ in ()).throw(ApiError("b 503", backend="b", reason="upstream-error"))
                ),
            ],
            max_workers=1,
        )

        assert result.items == []
        assert result.all_failed is True
        assert set(result.failed_sources) == {"a", "b"}

    def test_source_allowlist_preserves_available_order(self):
        from animedex.agg.search import _select_sources

        assert _select_sources(["anilist", "jikan", "kitsu"], "kitsu,anilist") == ["anilist", "kitsu"]

    def test_source_allowlist_rejects_unknown_names(self):
        from animedex.agg.search import _select_sources
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="unknown source") as excinfo:
            _select_sources(["anilist", "jikan"], "anilist,nope")
        assert excinfo.value.reason == "bad-args"

    def test_selftest_runs(self):
        import animedex.agg._fanout as fanout

        assert fanout.selftest() is True
