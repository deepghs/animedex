"""
Tests for :mod:`animedex.render.raw`.

Pins the four output renderers:

* ``render_body`` - default, body only.
* ``render_include`` - ``-i`` / curl-style headers + body.
* ``render_head`` - ``-I`` / headers only.
* ``render_debug`` - ``--debug`` / structured JSON envelope.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


@pytest.fixture
def envelope():
    from animedex.api._envelope import (
        RawCacheInfo,
        RawRequest,
        RawResponse,
        RawTiming,
    )

    return RawResponse(
        backend="anilist",
        request=RawRequest(
            method="POST",
            url="https://graphql.anilist.co/",
            headers={"User-Agent": "animedex/0.0.1", "Content-Type": "application/json"},
            body_preview='{"query":"{ Media(id:154587){ id } }"}',
        ),
        redirects=[],
        status=200,
        response_headers={
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "30",
            "X-RateLimit-Remaining": "28",
        },
        body_bytes=b'{"data":{"Media":{"id":154587}}}',
        body_text='{"data":{"Media":{"id":154587}}}',
        timing=RawTiming(total_ms=612.4, rate_limit_wait_ms=0.1, request_ms=612.3),
        cache=RawCacheInfo(hit=False, key="anilist:abc123"),
    )


@pytest.fixture
def envelope_cache_hit():
    from animedex.api._envelope import (
        RawCacheInfo,
        RawRequest,
        RawResponse,
        RawTiming,
    )

    return RawResponse(
        backend="jikan",
        request=RawRequest(
            method="GET", url="https://api.jikan.moe/v4/anime/52991", headers={"User-Agent": "animedex/0.0.1"}
        ),
        status=200,
        response_headers={"Content-Type": "application/json"},
        body_bytes=b'{"data":{"mal_id":52991}}',
        body_text='{"data":{"mal_id":52991}}',
        timing=RawTiming(total_ms=0.4, rate_limit_wait_ms=0, request_ms=0),
        cache=RawCacheInfo(
            hit=True,
            key="jikan:abc",
            ttl_remaining_s=245892,
            fetched_at=datetime(2026, 5, 7, 8, 13, 21, tzinfo=timezone.utc),
        ),
    )


class TestRenderBody:
    def test_returns_body_text_when_decodable(self, envelope):
        from animedex.render.raw import render_body

        out = render_body(envelope)
        assert out == '{"data":{"Media":{"id":154587}}}'

    def test_falls_back_to_bytes_repr_when_not_decodable(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_body

        env = RawResponse(
            backend="trace",
            request=RawRequest(method="GET", url="https://api.trace.moe/x", headers={}),
            status=200,
            response_headers={},
            body_bytes=b"\xff\xd8\xff\xe0",
            body_text=None,
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        out = render_body(env)
        assert isinstance(out, (bytes, str))


class TestRenderInclude:
    def test_status_line_first(self, envelope):
        from animedex.render.raw import render_include

        out = render_include(envelope)
        first_line = out.split("\n", 1)[0]
        assert "200" in first_line

    def test_headers_present(self, envelope):
        from animedex.render.raw import render_include

        out = render_include(envelope)
        assert "x-ratelimit-limit: 30" in out.lower() or "X-RateLimit-Limit: 30" in out

    def test_body_after_blank_line(self, envelope):
        from animedex.render.raw import render_include

        out = render_include(envelope)
        # Headers separated from body by an empty line.
        assert "\n\n" in out
        body_part = out.split("\n\n", 1)[1]
        assert "154587" in body_part


class TestRenderHead:
    def test_status_line(self, envelope):
        from animedex.render.raw import render_head

        out = render_head(envelope)
        assert "200" in out.split("\n", 1)[0]

    def test_no_body(self, envelope):
        from animedex.render.raw import render_head

        out = render_head(envelope)
        assert "154587" not in out

    def test_headers_present(self, envelope):
        from animedex.render.raw import render_head

        out = render_head(envelope)
        assert "Content-Type" in out


class TestRenderDebug:
    def test_returns_valid_json(self, envelope):
        from animedex.render.raw import render_debug

        out = render_debug(envelope)
        decoded = json.loads(out)
        assert decoded["backend"] == "anilist"
        assert decoded["status"] == 200
        assert decoded["request"]["url"] == "https://graphql.anilist.co/"
        assert decoded["timing"]["total_ms"] == 612.4
        assert decoded["cache"]["hit"] is False

    def test_includes_redacted_request_headers(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
            redact_headers,
        )
        from animedex.render.raw import render_debug

        # 30-char token so the fingerprint form fires (threshold is 24).
        original_headers = {"Authorization": "Bearer abcd1234567890XYZabcd1234XYZ99", "User-Agent": "animedex/0.0.1"}
        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="GET", url="https://x.invalid/", headers=redact_headers(original_headers)),
            status=200,
            response_headers={},
            body_bytes=b"",
            body_text="",
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        out = render_debug(env)
        decoded = json.loads(out)
        assert "abcd1234567890XYZabcd1234" not in out  # raw value never appears
        assert "(len=" in decoded["request"]["headers"]["Authorization"]

    def test_cache_hit_envelope_has_zero_request_ms(self, envelope_cache_hit):
        from animedex.render.raw import render_debug

        out = render_debug(envelope_cache_hit)
        decoded = json.loads(out)
        assert decoded["cache"]["hit"] is True
        assert decoded["cache"]["ttl_remaining_s"] == 245892
        assert decoded["cache"]["fetched_at"] is not None
        assert decoded["timing"]["request_ms"] == 0

    def test_body_truncated_above_default_cap(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_debug

        big_body = b"x" * 100000
        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
            status=200,
            response_headers={},
            body_bytes=big_body,
            body_text="x" * 100000,
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        out = render_debug(env)
        decoded = json.loads(out)
        assert decoded["body_truncated_at_bytes"] is not None
        assert len(decoded["body_text"]) <= 65536  # default 64 KiB cap

    def test_full_body_when_requested(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_debug

        big_body = b"x" * 100000
        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
            status=200,
            response_headers={},
            body_bytes=big_body,
            body_text="x" * 100000,
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        out = render_debug(env, full_body=True)
        decoded = json.loads(out)
        assert decoded.get("body_truncated_at_bytes") is None
        assert len(decoded["body_text"]) == 100000

    def test_firewall_rejected_envelope(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_debug

        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="DELETE", url="https://x.invalid/", headers={}),
            status=0,
            response_headers={},
            body_bytes=b"",
            body_text="",
            timing=RawTiming(total_ms=0.5, rate_limit_wait_ms=0, request_ms=0),
            cache=RawCacheInfo(hit=False),
            firewall_rejected={"reason": "read-only", "message": "DELETE / not permitted on anilist"},
        )

        out = render_debug(env)
        decoded = json.loads(out)
        assert decoded["firewall_rejected"]["reason"] == "read-only"
        assert decoded["status"] == 0


class TestRenderDebugBinaryBody:
    """Regression for review M2: render_debug crashed on any non-UTF-8
    body because pydantic v2's default bytes serialiser tries
    .decode('utf-8') before the renderer's truncation logic runs."""

    def test_jpeg_header_bytes_render_to_base64(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_debug

        env = RawResponse(
            backend="trace",
            request=RawRequest(method="GET", url="https://api.trace.moe/x", headers={}),
            status=200,
            response_headers={"Content-Type": "image/jpeg"},
            body_bytes=b"\xff\xd8\xff\xe0",  # JPEG SOI + APP0 marker
            body_text=None,
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        # Should not raise; should emit base64 in body_bytes.
        out = render_debug(env)
        import base64

        decoded = json.loads(out)
        assert decoded["body_text"] is None
        # body_bytes is rendered as base64 in --debug mode for binary.
        assert decoded["body_bytes"] == base64.b64encode(b"\xff\xd8\xff\xe0").decode("ascii")

    def test_png_bytes_truncate_under_default_cap(self):
        """Larger binary body still truncates without crashing."""
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_debug

        big_jpeg = b"\xff\xd8\xff\xe0" + (b"\x00" * 100_000)
        env = RawResponse(
            backend="trace",
            request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
            status=200,
            response_headers={},
            body_bytes=big_jpeg,
            body_text=None,
            timing=RawTiming(total_ms=1, rate_limit_wait_ms=0, request_ms=1),
            cache=RawCacheInfo(hit=False),
        )

        out = render_debug(env)
        decoded = json.loads(out)
        assert decoded["body_truncated_at_bytes"] is not None
        assert len(decoded["body_bytes"]) <= 65536


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import raw

        assert raw.selftest() is True
