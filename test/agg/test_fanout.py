"""Unit tests for aggregate fan-out helper branches."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestFanoutBranches:
    def test_normalises_none_tuple_dict_rows_object_and_scalar(self):
        from animedex.agg._fanout import _normalise_items
        from animedex.models.common import ApiError

        class Rows:
            rows = [1, 2]

        assert _normalise_items(None) == []
        assert _normalise_items((1, 2)) == [1, 2]
        assert _normalise_items({"items": [3, 4]}) == [3, 4]
        assert _normalise_items({"data": (5, 6)}) == [5, 6]
        assert _normalise_items(Rows()) == [1, 2]
        assert _normalise_items("x") == ["x"]
        with pytest.raises(ApiError) as err:
            _normalise_items({"meta": {"total": 2}})
        assert err.value.reason == "upstream-shape"

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

    def test_selftest_runs(self):
        import animedex.agg._fanout as fanout

        assert fanout.selftest() is True
