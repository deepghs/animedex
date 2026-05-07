"""
Tests for :mod:`animedex.transport.http`.

The :class:`~animedex.transport.http.HttpClient` is the surface every
backend reaches HTTP through. It composes the User-Agent injector,
the rate limiter, and the read-only firewall on top of a
``requests.Session``. The tests pin: UA injection, read-only
enforcement before a request goes out, rate-limiter consultation,
and the ``Via`` header strip required by MangaDex's contract
(``plans/02 §7``).
"""

from __future__ import annotations

import pytest
import responses


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"now": 0.0, "slept": 0.0}

    def now():
        return state["now"]

    def sleep(seconds):
        state["slept"] += seconds
        state["now"] += seconds

    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", now)
    monkeypatch.setattr("animedex.transport.ratelimit._sleep", sleep)
    return state


class TestHttpClientGet:
    @responses.activate
    def test_basic_get(self, fake_clock):
        from animedex.transport.http import HttpClient

        responses.add(
            responses.GET,
            "https://upstream.invalid/x",
            json={"ok": True},
            status=200,
        )

        client = HttpClient(backend="anilist", base_url="https://upstream.invalid")
        result = client.get("/x")

        assert result.json() == {"ok": True}

    @responses.activate
    def test_get_injects_user_agent(self, fake_clock):
        from animedex.transport.http import HttpClient

        responses.add(
            responses.GET,
            "https://upstream.invalid/x",
            json={},
            status=200,
        )

        client = HttpClient(backend="anilist", base_url="https://upstream.invalid")
        client.get("/x")

        assert "animedex/" in responses.calls[0].request.headers["User-Agent"]

    @responses.activate
    def test_get_strips_via_header(self, fake_clock):
        """MangaDex forbids the ``Via`` header (plan 02 §7)."""
        from animedex.transport.http import HttpClient

        responses.add(
            responses.GET,
            "https://upstream.invalid/x",
            json={},
            status=200,
        )

        client = HttpClient(backend="mangadex", base_url="https://upstream.invalid")
        client.get("/x", headers={"Via": "1.1 someproxy"})

        assert "Via" not in responses.calls[0].request.headers


class TestHttpClientReadOnlyFirewall:
    def test_put_rejected_before_request(self, fake_clock):
        from animedex.models.common import ApiError
        from animedex.transport.http import HttpClient

        client = HttpClient(backend="anilist", base_url="https://upstream.invalid")
        with pytest.raises(ApiError) as ei:
            client.request("PUT", "/x")
        assert ei.value.reason == "read-only"

    def test_post_to_anilist_root_allowed(self, fake_clock):
        from animedex.transport.http import HttpClient

        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, "https://upstream.invalid/", json={}, status=200)
            client = HttpClient(backend="anilist", base_url="https://upstream.invalid")
            client.request("POST", "/")


class TestHttpClientRateLimiter:
    @responses.activate
    def test_consults_ratelimiter(self, fake_clock):
        from animedex.transport.http import HttpClient
        from animedex.transport.ratelimit import RateLimitRegistry

        responses.add(responses.GET, "https://upstream.invalid/x", json={}, status=200)
        responses.add(responses.GET, "https://upstream.invalid/x", json={}, status=200)

        registry = RateLimitRegistry()
        registry.register("anilist", capacity=1, refill_per_second=2.0)

        client = HttpClient(
            backend="anilist",
            base_url="https://upstream.invalid",
            rate_limit_registry=registry,
        )
        client.get("/x")
        client.get("/x")

        assert fake_clock["slept"] > 0


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.transport import http

        assert http.selftest() is True
