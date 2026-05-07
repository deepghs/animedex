"""
Tests for :mod:`animedex.api._envelope`.

Covers the five envelope dataclasses (RawRequest, RawRedirectHop,
RawTiming, RawCacheInfo, RawResponse) and the credential-redaction
helpers (redact_credential_value, redact_headers).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


class TestRedactCredentialValue:
    def test_short_value_uses_redacted_len_form(self):
        from animedex.api._envelope import redact_credential_value

        assert redact_credential_value("abc") == "<redacted len=3>"
        assert redact_credential_value("abcdefghi") == "<redacted len=9>"
        # Per review m2: raise the fingerprint threshold to 24 chars
        # so a fingerprinted token has >=16 unrevealed chars in the
        # middle (was 4, brute-forceable). 12-char tokens now stay
        # fully redacted.
        assert redact_credential_value("abcdefghijk") == "<redacted len=11>"
        assert redact_credential_value("abcdef123456") == "<redacted len=12>"
        assert redact_credential_value("abcdef1234567890XYZ123") == "<redacted len=22>"
        assert redact_credential_value("abcdef1234567890XYZ12AB") == "<redacted len=23>"

    def test_long_value_uses_fingerprint_form(self):
        from animedex.api._envelope import redact_credential_value

        # 24 chars: 4 head + 16 hidden + 4 tail = (len=24)
        out_24 = redact_credential_value("abcd12345678abcd1234xyzw")
        assert out_24 == "abcd...xyzw (len=24)"
        # Longer tokens unchanged in form
        out_25 = redact_credential_value("abcd1234567890XYZ12abXY99")
        assert out_25 == "abcd...XY99 (len=25)"

    def test_jwt_style_value_keeps_unique_suffix(self):
        from animedex.api._envelope import redact_credential_value

        jwt = "eyJ0eXAiOiJKV1Q" + "X" * 200 + "Z9z9"
        out = redact_credential_value(jwt)
        assert out.startswith("eyJ0...")
        assert "Z9z9" in out
        assert "(len=" in out

    def test_empty_string_uses_redacted_len_zero(self):
        from animedex.api._envelope import redact_credential_value

        assert redact_credential_value("") == "<redacted len=0>"


class TestRedactHeaders:
    @pytest.mark.parametrize(
        "header_name",
        [
            "Authorization",
            "authorization",
            "Cookie",
            "cookie",
            "X-Api-Key",
            "x-api-key",
            "X-Api_Key",
            "X-Trace-Key",
            "X-Auth-Token",
            "ApiKey",
            "Some-Token",
            "MY-SECRET",
        ],
    )
    def test_credential_headers_redacted(self, header_name):
        from animedex.api._envelope import redact_headers

        # Use a 30-char value so the fingerprint form (head+tail) fires;
        # below the 24-char threshold the value would get the
        # <redacted len=N> form which doesn't preserve "(len=...)".
        headers = {header_name: "abcd1234567890XYZ12abcd1234567"}
        redacted = redact_headers(headers)
        assert "1234567890" not in redacted[header_name]
        assert "(len=30)" in redacted[header_name]

    @pytest.mark.parametrize(
        "header_name",
        [
            "Content-Type",
            "User-Agent",
            "Accept",
            "X-RateLimit-Limit",
            "Date",
            "Via",
        ],
    )
    def test_non_credential_headers_unchanged(self, header_name):
        from animedex.api._envelope import redact_headers

        headers = {header_name: "some-value-that-stays"}
        assert redact_headers(headers)[header_name] == "some-value-that-stays"

    def test_authorization_bearer_keeps_scheme_prefix(self):
        from animedex.api._envelope import redact_headers

        headers = {"Authorization": "Bearer abcd1234567890XYZ12abcd1234567"}
        out = redact_headers(headers)["Authorization"]
        assert out.startswith("Bearer ")
        assert "1234567890" not in out
        assert "(len=" in out

    def test_authorization_basic_keeps_scheme_prefix(self):
        from animedex.api._envelope import redact_headers

        headers = {"Authorization": "Basic dXNlcjpzZWNyZXRwYXNzd29yZA=="}
        out = redact_headers(headers)["Authorization"]
        assert out.startswith("Basic ")
        assert "secret" not in out

    def test_cookie_each_value_redacted(self):
        from animedex.api._envelope import redact_headers

        headers = {"Cookie": "session=abcd1234567890XYZ12; csrf=AAAA1111BBBB2222"}
        out = redact_headers(headers)["Cookie"]
        assert "session=" in out
        assert "csrf=" in out
        assert "1234567890" not in out
        assert "1111BBBB" not in out

    def test_returns_new_dict(self):
        from animedex.api._envelope import redact_headers

        original = {"Authorization": "Bearer abcd1234567890XYZ12"}
        redact_headers(original)
        assert original["Authorization"] == "Bearer abcd1234567890XYZ12"


class TestRawRequest:
    def test_minimal_construction(self):
        from animedex.api._envelope import RawRequest

        r = RawRequest(method="GET", url="https://x.invalid/y", headers={"User-Agent": "animedex/0.0.1"})

        assert r.method == "GET"
        assert r.headers == {"User-Agent": "animedex/0.0.1"}
        assert r.body_preview is None

    def test_round_trip_json(self):
        from animedex.api._envelope import RawRequest

        r = RawRequest(method="POST", url="https://x.invalid/", headers={}, body_preview='{"a":1}')
        assert RawRequest.model_validate_json(r.model_dump_json()) == r


class TestRawRedirectHop:
    def test_construction(self):
        from animedex.api._envelope import RawRedirectHop

        h = RawRedirectHop(
            status=301,
            headers={"Location": "https://new.invalid/x"},
            from_url="https://old.invalid/x",
            to_url="https://new.invalid/x",
            elapsed_ms=12.3,
        )
        assert h.status == 301
        assert h.elapsed_ms == 12.3


class TestRawTiming:
    def test_construction(self):
        from animedex.api._envelope import RawTiming

        t = RawTiming(total_ms=100.0, rate_limit_wait_ms=10.0, request_ms=90.0)
        assert t.total_ms == 100.0


class TestRawCacheInfo:
    def test_miss(self):
        from animedex.api._envelope import RawCacheInfo

        c = RawCacheInfo(hit=False)
        assert c.hit is False
        assert c.key is None
        assert c.ttl_remaining_s is None
        assert c.fetched_at is None

    def test_hit(self):
        from animedex.api._envelope import RawCacheInfo

        c = RawCacheInfo(
            hit=True,
            key="anilist:abc123",
            ttl_remaining_s=3600,
            fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
        )
        assert c.hit is True
        assert c.ttl_remaining_s == 3600


class TestRawResponse:
    def test_minimal_construction(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )

        r = RawResponse(
            backend="anilist",
            request=RawRequest(method="POST", url="https://graphql.anilist.co/", headers={}),
            status=200,
            response_headers={"Content-Type": "application/json"},
            body_bytes=b'{"data":{}}',
            body_text='{"data":{}}',
            timing=RawTiming(total_ms=100, rate_limit_wait_ms=0, request_ms=100),
            cache=RawCacheInfo(hit=False),
        )
        assert r.status == 200
        assert r.redirects == []
        assert r.firewall_rejected is None

    def test_firewall_rejected(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )

        r = RawResponse(
            backend="anilist",
            request=RawRequest(method="DELETE", url="https://graphql.anilist.co/", headers={}),
            status=0,
            response_headers={},
            body_bytes=b"",
            body_text="",
            timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0, request_ms=0),
            cache=RawCacheInfo(hit=False),
            firewall_rejected={"reason": "read-only", "message": "DELETE not permitted"},
        )
        assert r.firewall_rejected["reason"] == "read-only"

    def test_round_trip_json(self):
        from animedex.api._envelope import (
            RawCacheInfo,
            RawRequest,
            RawResponse,
            RawTiming,
        )

        r = RawResponse(
            backend="jikan",
            request=RawRequest(method="GET", url="https://api.jikan.moe/v4/anime/52991", headers={}),
            status=200,
            response_headers={"Content-Type": "application/json"},
            body_bytes=b"{}",
            body_text="{}",
            timing=RawTiming(total_ms=1.0, rate_limit_wait_ms=0, request_ms=1.0),
            cache=RawCacheInfo(hit=False),
        )
        assert RawResponse.model_validate_json(r.model_dump_json()) == r


class TestBodyTextBytesInvariant:
    """Per review m7: ``body_text`` and ``body_bytes`` must agree.

    Either ``body_text == body_bytes.decode('utf-8')`` or
    ``body_text is None`` (the bytes are not valid UTF-8). Anything
    else means cache-hit reconstruction has drifted from the live-call
    path, or a caller has hand-built an inconsistent envelope.
    """

    def _envelope_kwargs(self):
        from animedex.api._envelope import RawCacheInfo, RawRequest, RawTiming

        return dict(
            backend="anilist",
            request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
            status=200,
            response_headers={},
            timing=RawTiming(total_ms=0.1, rate_limit_wait_ms=0, request_ms=0.1),
            cache=RawCacheInfo(hit=False),
        )

    def test_text_must_match_bytes(self):
        from pydantic import ValidationError

        from animedex.api._envelope import RawResponse

        with pytest.raises(ValidationError, match="body_text.*body_bytes"):
            RawResponse(body_bytes=b'{"a":1}', body_text="something else", **self._envelope_kwargs())

    def test_text_must_be_none_when_bytes_are_not_utf8(self):
        from pydantic import ValidationError

        from animedex.api._envelope import RawResponse

        with pytest.raises(ValidationError, match="body_text.*body_bytes"):
            RawResponse(body_bytes=b"\xff\xd8\xff\xe0", body_text="not none", **self._envelope_kwargs())

    def test_matching_text_and_bytes_passes(self):
        from animedex.api._envelope import RawResponse

        # Sanity: the happy path remains constructible.
        r = RawResponse(body_bytes=b'{"ok":true}', body_text='{"ok":true}', **self._envelope_kwargs())
        assert r.body_text == '{"ok":true}'

    def test_none_text_with_binary_bytes_passes(self):
        from animedex.api._envelope import RawResponse

        r = RawResponse(body_bytes=b"\xff\xd8\xff\xe0", body_text=None, **self._envelope_kwargs())
        assert r.body_text is None

    def test_none_text_with_decodable_bytes_rejected(self):
        from pydantic import ValidationError

        from animedex.api._envelope import RawResponse

        # Bytes ARE valid UTF-8, so body_text must be the decoded form
        # (not None). Catches the live-call/cache-hit drift the
        # invariant is meant to lock down.
        with pytest.raises(ValidationError, match="body_text.*body_bytes"):
            RawResponse(body_bytes=b'{"ok":true}', body_text=None, **self._envelope_kwargs())
