"""
Tests for :mod:`animedex.api._dispatch`.

Covers the full envelope assembly: pre-call URL/header composition,
firewall rejection, rate-limit timing capture, cache lookup + write,
HTTP execution including the redirect chain, body decoding, and
final RawResponse construction.
"""

from __future__ import annotations

import pytest
import responses


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    """Deterministic clock for ratelimit + cache."""
    from datetime import datetime, timezone

    state = {
        "rl_now": 0.0,
        "rl_slept": 0.0,
        "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc),
    }

    def rl_now():
        return state["rl_now"]

    def rl_sleep(s):
        state["rl_slept"] += s
        state["rl_now"] += s

    def cache_now():
        return state["cache_now"]

    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", rl_now)
    monkeypatch.setattr("animedex.transport.ratelimit._sleep", rl_sleep)
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", cache_now)
    return state


@pytest.fixture
def cache(tmp_path, fake_clock):
    from animedex.cache.sqlite import SqliteCache

    return SqliteCache(path=tmp_path / "dispatch-test.sqlite")


class TestSimpleCall:
    @responses.activate
    def test_anilist_200_response(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.POST,
            "https://graphql.anilist.co/",
            json={"data": {"Media": {"id": 154587}}},
            status=200,
            headers={"X-RateLimit-Limit": "30"},
        )

        raw = call(
            backend="anilist",
            path="/",
            method="POST",
            json_body={"query": "{ Media(id:154587){ id } }"},
            cache=cache,
        )

        assert raw.backend == "anilist"
        assert raw.status == 200
        assert raw.firewall_rejected is None
        assert raw.cache.hit is False
        assert raw.body_text is not None
        assert "154587" in raw.body_text
        assert raw.timing.request_ms >= 0

    @responses.activate
    def test_jikan_200_response(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {"mal_id": 52991, "title": "Frieren"}},
            status=200,
        )

        raw = call(backend="jikan", path="/anime/52991", cache=cache)

        assert raw.status == 200
        assert raw.request.url == "https://api.jikan.moe/v4/anime/52991"
        assert raw.request.method == "GET"
        assert "User-Agent" in raw.request.headers
        assert raw.request.headers["User-Agent"] == "animedex/0.0.1"

    @responses.activate
    def test_404_response_passes_through(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/99999999",
            json={"status": 404, "type": "BadResponseException", "message": "Resource does not exist"},
            status=404,
        )

        raw = call(backend="jikan", path="/anime/99999999", cache=cache)

        assert raw.status == 404
        assert raw.firewall_rejected is None
        assert "BadResponseException" in raw.body_text


class TestFirewallRejection:
    def test_delete_rejected_before_request(self, fake_clock, cache):
        from animedex.api._dispatch import call

        raw = call(backend="anilist", path="/", method="DELETE", cache=cache)

        assert raw.firewall_rejected is not None
        assert raw.firewall_rejected["reason"] == "read-only"
        assert raw.status == 0
        assert raw.body_bytes == b""
        # The request the user attempted is still recorded.
        assert raw.request.method == "DELETE"

    def test_unknown_backend_rejected(self, fake_clock, cache):
        from animedex.api._dispatch import call

        raw = call(backend="not-a-backend", path="/", cache=cache)

        assert raw.firewall_rejected is not None
        assert raw.firewall_rejected["reason"] == "unknown-backend"


class TestRedirectChain:
    @responses.activate
    def test_follows_301_and_records_hop(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/old-path",
            status=301,
            headers={"Location": "https://api.jikan.moe/v4/anime/52991"},
        )
        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {"mal_id": 52991}},
            status=200,
        )

        raw = call(backend="jikan", path="/old-path", cache=cache)

        assert raw.status == 200
        assert len(raw.redirects) == 1
        assert raw.redirects[0].status == 301
        assert raw.redirects[0].to_url == "https://api.jikan.moe/v4/anime/52991"

    @responses.activate
    def test_no_follow_returns_3xx_directly(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/old-path",
            status=302,
            headers={"Location": "https://api.jikan.moe/v4/new-path"},
        )

        raw = call(backend="jikan", path="/old-path", cache=cache, follow_redirects=False)

        assert raw.status == 302
        assert raw.redirects == []


class TestCacheBehavior:
    @responses.activate
    def test_cache_miss_writes_then_hit(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {"mal_id": 52991}},
            status=200,
            headers={"X-Cache-Status": "MISS"},
        )

        first = call(backend="jikan", path="/anime/52991", cache=cache, cache_ttl=3600)
        assert first.cache.hit is False
        assert first.status == 200

        # No second mock added; the second call must come from cache.
        second = call(backend="jikan", path="/anime/52991", cache=cache, cache_ttl=3600)
        assert second.cache.hit is True
        assert second.status == 200
        assert second.body_text == first.body_text
        # Cached headers preserved.
        assert second.response_headers.get("X-Cache-Status") == "MISS"
        # Cache hit timing should be near-zero.
        assert second.timing.request_ms == 0
        assert second.cache.fetched_at is not None
        assert second.cache.ttl_remaining_s is not None

    @responses.activate
    def test_no_cache_skips_lookup_and_write(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {"mal_id": 52991}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {"mal_id": 52991, "alt": True}},
            status=200,
        )

        first = call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True)
        second = call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True)

        assert first.cache.hit is False
        assert second.cache.hit is False
        # Different bodies prove both went out.
        assert "alt" in second.body_text


class TestRequestSnapshotRedaction:
    @responses.activate
    def test_authorization_header_is_redacted(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        raw = call(
            backend="jikan",
            path="/anime/52991",
            headers={"Authorization": "Bearer aaaaaaaaaaaaaaaaaaaaa"},
            cache=cache,
        )

        # The on-the-wire Authorization header was sent (responses
        # captures the actual outgoing headers in responses.calls), but
        # the envelope's request.headers must NOT contain the raw
        # value.
        assert "aaaaaaaaaaaaaaaaaaaa" not in raw.request.headers["Authorization"]
        assert raw.request.headers["Authorization"].startswith("Bearer ")
        assert "(len=" in raw.request.headers["Authorization"]


class TestUnknownBackendRouting:
    def test_known_backend_resolves(self, fake_clock, cache):
        from animedex.api._dispatch import resolve_base_url

        assert resolve_base_url("anilist") == "https://graphql.anilist.co"
        assert resolve_base_url("jikan") == "https://api.jikan.moe/v4"
        assert resolve_base_url("kitsu") == "https://kitsu.io/api/edge"
        assert resolve_base_url("mangadex") == "https://api.mangadex.org"
        assert resolve_base_url("trace") == "https://api.trace.moe"
        assert resolve_base_url("danbooru") == "https://danbooru.donmai.us"
        assert resolve_base_url("shikimori") == "https://shikimori.io"
        assert resolve_base_url("ann") == "https://cdn.animenewsnetwork.com/encyclopedia"

    def test_unknown_backend_raises_value_error(self):
        from animedex.api._dispatch import resolve_base_url

        with pytest.raises(KeyError):
            resolve_base_url("not-a-backend")
