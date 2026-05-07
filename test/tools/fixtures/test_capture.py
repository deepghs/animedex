"""Tests for :mod:`tools.fixtures.capture`.

Phase-1 review M1: capture-time scrub of response headers that carry
the captor's IP, session cookies, or other host-side fingerprints.
Without this, every committed YAML in ``test/fixtures/`` leaks the
captor's egress IP via Shikimori's DDoS-Guard ``__ddg9_=<ip>`` cookie.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestScrubResponseHeaders:
    """The capture tool must scrub the headers a fixture is allowed to
    persist before the YAML is written to disk."""

    def test_set_cookie_is_replaced(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers(
            {"Set-Cookie": "__ddg9_=198.51.100.99; Path=/", "Content-Type": "application/json"}
        )
        assert out["Set-Cookie"] == "<scrubbed-at-capture>"
        assert out["Content-Type"] == "application/json"

    def test_x_forwarded_for_is_replaced(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers({"X-Forwarded-For": "203.0.113.7"})
        assert out["X-Forwarded-For"] == "<scrubbed-at-capture>"

    def test_x_real_ip_is_replaced(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers({"X-Real-IP": "203.0.113.7"})
        assert out["X-Real-IP"] == "<scrubbed-at-capture>"

    def test_cf_connecting_ip_is_replaced(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers({"CF-Connecting-IP": "203.0.113.7"})
        assert out["CF-Connecting-IP"] == "<scrubbed-at-capture>"

    def test_via_is_replaced(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers({"Via": "1.1 proxy.internal:8080"})
        assert out["Via"] == "<scrubbed-at-capture>"

    def test_match_is_case_insensitive(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers({"set-cookie": "session=abc", "X-FORWARDED-FOR": "1.2.3.4"})
        assert out["set-cookie"] == "<scrubbed-at-capture>"
        assert out["X-FORWARDED-FOR"] == "<scrubbed-at-capture>"

    def test_unrelated_headers_pass_through(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        out = scrub_capture_response_headers(
            {
                "Date": "Thu, 07 May 2026 00:00:00 GMT",
                "Cache-Control": "max-age=600",
                "Content-Type": "application/json",
            }
        )
        assert out == {
            "Date": "Thu, 07 May 2026 00:00:00 GMT",
            "Cache-Control": "max-age=600",
            "Content-Type": "application/json",
        }

    def test_returns_new_dict_rather_than_mutating(self):
        from tools.fixtures.capture import scrub_capture_response_headers

        original = {"Set-Cookie": "__ddg9_=1.2.3.4"}
        out = scrub_capture_response_headers(original)
        assert original["Set-Cookie"] == "__ddg9_=1.2.3.4"
        assert out["Set-Cookie"] == "<scrubbed-at-capture>"


class TestReplacePublicIpsWithPlaceholder:
    """Per review M1 + user-feedback follow-up: hardcoding "the
    captor's IP" in the scrub helper still leaks that IP into the
    helper's source. Replace generically — any public IPv4 in the
    text becomes the RFC-5737 placeholder, and private / loopback /
    documentation ranges pass through unchanged.
    """

    def test_arbitrary_public_ip_is_replaced(self):
        from tools.fixtures.capture import replace_public_ips_with_placeholder

        out = replace_public_ips_with_placeholder("client=8.8.8.8 routed=1.1.1.1")
        assert "8.8.8.8" not in out
        assert "1.1.1.1" not in out
        # Both replaced with the same placeholder.
        assert out.count("203.0.113.42") == 2

    def test_private_addresses_are_kept(self):
        from tools.fixtures.capture import replace_public_ips_with_placeholder

        original = "intranet=10.0.0.1 loopback=127.0.0.1 lan=192.168.1.5"
        assert replace_public_ips_with_placeholder(original) == original

    def test_documentation_addresses_are_kept(self):
        """RFC-5737 reserved ranges are explicit placeholders;
        treating them as leaks would be a self-fulfilling false
        positive."""
        from tools.fixtures.capture import replace_public_ips_with_placeholder

        original = "doc1=192.0.2.1 doc2=198.51.100.7 doc3=203.0.113.42"
        assert replace_public_ips_with_placeholder(original) == original

    def test_non_ip_text_passes_through(self):
        from tools.fixtures.capture import replace_public_ips_with_placeholder

        original = "version=1.2.3 build=4.5.6.7.8 (not an IP)"
        out = replace_public_ips_with_placeholder(original)
        # 4.5.6.7 is a real public IP, but "4.5.6.7.8" still embeds it
        # as a substring per word-boundary matching. That's acceptable
        # — better safe than sorry.
        assert "4.5.6.7" not in out

    def test_invalid_octet_passes_through(self):
        from tools.fixtures.capture import replace_public_ips_with_placeholder

        # "999.999.999.999" matches the regex but fails IPv4 parsing.
        original = "garbage=999.999.999.999"
        assert replace_public_ips_with_placeholder(original) == original


class TestNoPublicIpLeaksInFixtures:
    """Per review M1: a CI-grade guard that fails-closed on any
    public IPv4 address in ``test/fixtures/``. Without this, a future
    contributor running a raw capture script that bypasses the scrub
    helper can re-leak an IP into git history.

    The guard tolerates explicit placeholders
    (``203.0.113.x`` from RFC 5737, ``192.0.2.x``,
    ``198.51.100.x``) and private-range addresses (10.x, 172.16-31.x,
    192.168.x); they are documentation/test markers and carry no
    real-world identity.
    """

    def test_no_public_ipv4_in_fixtures(self):
        import ipaddress
        import re
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        fixtures = repo_root / "test" / "fixtures"

        # IPv4 dotted-quad pattern. The trailing word boundary check
        # avoids matching version strings like "1.2.3.45" - we then
        # validate each match through ``ipaddress`` to weed out
        # non-IPs.
        ipv4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
        leaks: dict[str, list[str]] = {}

        for path in sorted(fixtures.rglob("*.yaml")):
            text = path.read_text(encoding="utf-8")
            for match in ipv4.findall(text):
                try:
                    addr = ipaddress.IPv4Address(match)
                except ipaddress.AddressValueError:
                    continue
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    continue
                # RFC-5737 reserved-for-documentation ranges are
                # explicit placeholders; allow them through.
                if (
                    addr in ipaddress.IPv4Network("192.0.2.0/24")
                    or addr in ipaddress.IPv4Network("198.51.100.0/24")
                    or addr in ipaddress.IPv4Network("203.0.113.0/24")
                ):
                    continue
                rel = path.relative_to(repo_root)
                leaks.setdefault(str(rel), []).append(match)

        assert not leaks, (
            "Public IPv4 addresses found in fixtures (privacy leak; review M1): "
            f"{leaks}. Use tools.fixtures.capture.scrub_capture_response_headers "
            "and add the leaked IP to tools/fixtures/scrub_existing.py:_BODY_IP_REPLACEMENTS, "
            "then re-run that script."
        )
