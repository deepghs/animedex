"""Trace.moe Python API tests.

``trace.quota()`` returns the common projection :class:`TraceQuota`,
which has no ``id`` field — so the caller's egress IP that the
upstream echoes back never reaches the common shape. (A power user
who actually wants ``id`` reaches for the rich
:class:`RawTraceQuota` directly; that is lossless per AGENTS §13.)
The /search mapper coerces the right field set.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from animedex.backends import trace as trace_api
from animedex.models.common import SourceTag
from animedex.models.trace import TraceHit, TraceQuota


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "trace"


def _src() -> SourceTag:
    return SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


class TestQuotaCommonShape:
    """``trace.quota()`` returns the common projection, which has no
    ``id`` field — so the upstream's caller-IP echo never appears on
    the returned object."""

    def test_common_quota_has_no_id_field(self, monkeypatch):
        # Stub the raw envelope so the mapper sees a /me payload
        # carrying the captor IP.
        from animedex.api import trace as raw_trace

        class _FakeEnvelope:
            firewall_rejected = None
            body_text = json.dumps(
                {"id": "203.0.113.42", "priority": 0, "concurrency": 1, "quota": 100, "quotaUsed": "18"}
            )

            class cache:
                hit = False

            class timing:
                rate_limit_wait_ms = 0

        monkeypatch.setattr(raw_trace, "call", lambda **kw: _FakeEnvelope())

        result = trace_api.quota()
        assert isinstance(result, TraceQuota)
        # No field on the model carries the IP.
        dumped = result.model_dump_json()
        assert "203.0.113.42" not in dumped
        # quotaUsed coerced from string to int.
        assert result.quota_used == 18

    def test_quota_used_string_coerced(self, monkeypatch):
        from animedex.api import trace as raw_trace

        class _Env:
            firewall_rejected = None
            body_text = json.dumps(
                {"id": "203.0.113.42", "priority": 0, "concurrency": 1, "quota": 100, "quotaUsed": "42"}
            )

            class cache:
                hit = False

            class timing:
                rate_limit_wait_ms = 0

        monkeypatch.setattr(raw_trace, "call", lambda **kw: _Env())
        assert trace_api.quota().quota_used == 42


class TestSearch:
    @pytest.mark.parametrize("path", sorted((FIXTURES / "search").glob("*.yaml")))
    def test_search_fixture_parses_into_hits(self, path, monkeypatch):
        fix = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = fix["response"].get("body_json")
        if body is None or not body.get("result"):
            pytest.skip("search fixture has no hits")
        from animedex.api import trace as raw_trace

        class _Env:
            firewall_rejected = None
            body_text = json.dumps(body)

            class cache:
                hit = False

            class timing:
                rate_limit_wait_ms = 0

        monkeypatch.setattr(raw_trace, "call", lambda **kw: _Env())
        hits = trace_api.search(image_url="https://example.invalid/x.jpg")
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
