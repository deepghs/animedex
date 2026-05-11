"""Unit tests for aggregate fan-out helper branches."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestFanoutBranches:
    def test_normalises_none_tuple_rows_object_and_scalar(self):
        from animedex.agg._fanout import _normalise_items

        class Rows:
            rows = [1, 2]

        assert _normalise_items(None) == []
        assert _normalise_items((1, 2)) == [1, 2]
        assert _normalise_items(Rows()) == [1, 2]
        assert _normalise_items("x") == ["x"]

    def test_http_status_absent_message_returns_none(self):
        from animedex.agg._fanout import _http_status_from_message

        assert _http_status_from_message("boom") is None

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
