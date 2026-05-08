"""Trace.moe Python API tests.

``trace.quota()`` returns the common projection :class:`TraceQuota`,
which has no ``id`` field — so the caller's egress IP that the
upstream echoes back never reaches the common shape. (A power user
who actually wants ``id`` reaches for the rich
:class:`RawTraceQuota` directly; that is lossless per AGENTS §13.)
The /search mapper coerces the right field set.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import trace as trace_api
from animedex.models.common import SourceTag
from animedex.models.trace import TraceHit, TraceQuota


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "trace"


def _src() -> SourceTag:
    return SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze the dispatcher clock so cache TTL math + ratelimit are
    deterministic. Only HTTP-adjacent OS-level seams are mocked, per
    the test discipline."""
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


class TestQuotaCommonShape:
    """``trace.quota()`` returns the common projection, which has no
    ``id`` field — so the upstream's caller-IP echo never appears on
    the returned object."""

    def test_common_quota_has_no_id_field(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={
                    "id": "203.0.113.42",
                    "priority": 0,
                    "concurrency": 1,
                    "quota": 100,
                    "quotaUsed": "18",
                },
                status=200,
            )
            result = trace_api.quota(no_cache=True)
        assert isinstance(result, TraceQuota)
        # No field on the common projection carries the IP.
        dumped = result.model_dump_json()
        assert "203.0.113.42" not in dumped
        # quotaUsed coerced from string to int.
        assert result.quota_used == 18

    def test_quota_used_string_coerced(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/me",
                json={
                    "id": "203.0.113.42",
                    "priority": 0,
                    "concurrency": 1,
                    "quota": 100,
                    "quotaUsed": "42",
                },
                status=200,
            )
            assert trace_api.quota(no_cache=True).quota_used == 42


class TestSearch:
    @pytest.mark.parametrize("path", sorted((FIXTURES / "search").glob("*.yaml")))
    def test_search_fixture_parses_into_hits(self, path, fake_clock):
        fix = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = fix["response"].get("body_json")
        if body is None or not body.get("result"):
            pytest.skip("search fixture has no hits")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.trace.moe/search",
                json=body,
                status=200,
            )
            hits = trace_api.search(image_url="https://example.invalid/x.jpg", no_cache=True)
        for h in hits:
            assert isinstance(h, TraceHit)
            assert h.anilist_id > 0
            assert 0.0 <= h.similarity <= 1.0


class TestSearchValidation:
    def test_both_url_and_bytes_raises(self):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="not both"):
            trace_api.search(image_url="https://x.invalid/a.jpg", raw_bytes=b"abc")

    def test_neither_url_nor_bytes_raises(self):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="required"):
            trace_api.search()
