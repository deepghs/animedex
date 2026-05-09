"""Coverage tests for the small edge branches inside
:mod:`animedex.api._dispatch`, :mod:`animedex.api.anilist`,
:mod:`animedex.api.kitsu`, and :mod:`animedex.render.raw`.

These cover code paths the broader test suite doesn't reach: body-
preview truncation, the request-header ``Via`` strip per AGENTS §0,
caller-supplied UTF-8-decoded body, anilist + kitsu header merging,
and the local-rejection status-line render path.
"""

from __future__ import annotations

import pytest
import responses


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    from datetime import datetime, timezone

    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr("animedex.transport.ratelimit._sleep", lambda s: state.update({"rl_now": state["rl_now"] + s}))
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


@pytest.fixture
def cache(tmp_path, fake_clock):
    from animedex.cache.sqlite import SqliteCache

    return SqliteCache(path=tmp_path / "edge.sqlite")


class TestJoinUtilityBranches:
    """``_join`` is the URL composer; it has two non-default branches:
    a path that is already a full URL and a path missing the leading
    slash."""

    def test_absolute_https_path_passes_through(self):
        from animedex.api._dispatch import _join

        assert _join("https://api.x/v1", "https://other.x/y") == "https://other.x/y"

    def test_absolute_http_path_passes_through(self):
        from animedex.api._dispatch import _join

        assert _join("https://api.x/v1", "http://other.x/y") == "http://other.x/y"

    def test_relative_path_without_leading_slash_is_normalised(self):
        from animedex.api._dispatch import _join

        assert _join("https://api.x/v1", "anime/1") == "https://api.x/v1/anime/1"

    def test_relative_path_with_leading_slash_unchanged(self):
        from animedex.api._dispatch import _join

        assert _join("https://api.x/v1", "/anime/1") == "https://api.x/v1/anime/1"


class TestSignatureRawBody:
    """The ``body`` kwarg of ``_signature`` covers the raw-bytes
    cache-key branch — distinct from json_body and from no-body."""

    def test_raw_body_changes_signature(self):
        from animedex.api._dispatch import _signature

        a = _signature("POST", "https://x.invalid/", None, None, b"payload-a")
        b = _signature("POST", "https://x.invalid/", None, None, b"payload-b")
        c = _signature("POST", "https://x.invalid/", None, None, None)
        assert a != b
        assert a != c
        assert b != c


class TestCacheHitNonUtf8Body:
    """When a cached row's payload bytes are not valid UTF-8, the
    cache-hit reconstruction must emit ``body_text=None`` rather than
    raise. This shadows the live-call decode-error fallback already
    covered by TestNonUtf8BodyPath, but on the read side."""

    @responses.activate
    def test_cache_hit_with_binary_payload_yields_body_text_none(self, fake_clock, cache):
        from animedex.api._dispatch import _signature, call

        sig = _signature("GET", "https://api.jikan.moe/v4/anime/1", None, None, None)
        cache.set_with_meta(
            "jikan",
            sig,
            b"\xff\xd8\xff\xe0",
            response_headers={"Content-Type": "image/jpeg"},
            ttl_seconds=60,
        )

        raw = call(backend="jikan", path="/anime/1", cache=cache)
        assert raw.cache.hit is True
        assert raw.body_bytes == b"\xff\xd8\xff\xe0"
        assert raw.body_text is None


class TestMakeBodyPreview:
    def test_long_text_is_truncated(self):
        from animedex.api._dispatch import _BODY_PREVIEW_BYTES, _make_body_preview

        text = "x" * (_BODY_PREVIEW_BYTES + 100)
        out = _make_body_preview(None, text.encode("utf-8"))
        assert out is not None
        assert out.endswith("...truncated")
        assert len(out) <= _BODY_PREVIEW_BYTES + len("...truncated")

    def test_short_text_returned_intact(self):
        from animedex.api._dispatch import _make_body_preview

        out = _make_body_preview(None, b"short text")
        assert out == "short text"

    def test_none_when_no_body(self):
        from animedex.api._dispatch import _make_body_preview

        assert _make_body_preview(None, None) is None

    def test_json_body_serialized(self):
        from animedex.api._dispatch import _make_body_preview

        out = _make_body_preview({"k": "v"}, None)
        assert out == '{"k": "v"}'

    def test_non_decodable_raw_body_falls_back_to_size_marker(self):
        """If ``raw_body`` lacks a usable ``.decode``, the helper
        falls through to the binary-marker. ``errors='replace'`` on
        bytes never raises, so we exercise the exception branch by
        passing a non-bytes object (e.g. a memoryview-like type
        without a ``.decode`` that fails for some reason)."""
        from animedex.api._dispatch import _make_body_preview

        class BadBytes:
            def __len__(self):
                return 99

            def decode(self, *_, **__):
                raise RuntimeError("synthetic decode failure")

        out = _make_body_preview(None, BadBytes())
        assert out == "<99 bytes binary>"


class TestViaHeaderStripped:
    """Per AGENTS §0: the dispatcher unconditionally strips a
    caller-supplied ``Via`` header (forbidden header for MangaDex,
    same risk surface elsewhere)."""

    @responses.activate
    def test_via_header_dropped_before_send(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/1", json={}, status=200)

        raw = call(
            backend="jikan",
            path="/anime/1",
            headers={"Via": "1.1 my.proxy", "X-Keep": "yes"},
            cache=cache,
            no_cache=True,
        )

        # Snapshot retains the user's intent through the request, but
        # ``Via`` is filtered out of the on-the-wire and snapshot
        # headers.
        assert "Via" not in raw.request.headers
        assert raw.request.headers.get("X-Keep") == "yes"


class TestNonUtf8BodyPath:
    """Per existing M2 fix, response bodies that are not valid UTF-8
    yield ``body_text=None`` and ``body_bytes`` carries the raw
    bytes."""

    @responses.activate
    def test_non_utf8_body_keeps_bytes_drops_text(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/1",
            body=b"\xff\xd8\xff\xe0",
            status=200,
            content_type="image/jpeg",
        )

        raw = call(backend="jikan", path="/anime/1", cache=cache, no_cache=True)
        assert raw.body_bytes == b"\xff\xd8\xff\xe0"
        assert raw.body_text is None


class TestAnilistHeaderMerge:
    """``anilist.call`` merges caller-supplied headers on top of its
    default ``Content-Type: application/json``."""

    @responses.activate
    def test_caller_headers_merged(self, fake_clock, cache):
        from animedex.api import anilist

        responses.add(responses.POST, "https://graphql.anilist.co/", json={"data": {}}, status=200)

        raw = anilist.call(
            query="{ x }",
            headers={"X-Custom": "v"},
            cache=cache,
            no_cache=True,
        )

        sent = responses.calls[-1].request.headers
        assert sent.get("Content-Type") == "application/json"
        assert sent.get("X-Custom") == "v"
        # The envelope's request snapshot reflects the same.
        assert raw.request.headers.get("X-Custom") == "v"


class TestKitsuHeaderMerge:
    """``kitsu.call`` merges caller headers on top of the JSON-API
    Accept default."""

    @responses.activate
    def test_default_accept_present_with_caller_override(self, fake_clock, cache):
        from animedex.api import kitsu

        responses.add(responses.GET, "https://kitsu.io/api/edge/anime/1", json={"data": {}}, status=200)

        raw = kitsu.call(
            path="/anime/1",
            headers={"X-Trace": "yes"},
            cache=cache,
            no_cache=True,
        )

        assert raw.request.headers.get("Accept") == "application/vnd.api+json"
        assert raw.request.headers.get("X-Trace") == "yes"


class TestLocalRejectionStatusLineRender:
    """``render.raw._format_status_line`` has a local-rejection
    branch that the regular envelope tests don't trigger directly."""

    def test_local_rejected_status_line_is_formatted(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_include

        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="DELETE", url="https://x.invalid/", headers={}),
            status=0,
            response_headers={},
            body_bytes=b"",
            body_text="",
            timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0.0, request_ms=0.0),
            cache=RawCacheInfo(hit=False),
            firewall_rejected={"reason": "unknown-backend", "message": "unknown backend"},
        )

        out = render_include(env)
        first = out.split("\n", 1)[0]
        assert "firewall-rejected" in first
        assert "unknown-backend" in first

    def test_local_rejected_without_reason_uses_default(self):
        """When the rejection dict omits ``reason``, the renderer
        falls back to the literal ``rejected`` string."""
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )
        from animedex.render.raw import render_include

        env = RawResponse(
            backend="anilist",
            request=RawRequest(method="DELETE", url="https://x.invalid/", headers={}),
            status=0,
            response_headers={},
            body_bytes=b"",
            body_text="",
            timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0.0, request_ms=0.0),
            cache=RawCacheInfo(hit=False),
            firewall_rejected={"message": "no reason key"},
        )

        first = render_include(env).split("\n", 1)[0]
        assert "rejected" in first
