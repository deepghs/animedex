"""
Tests for :mod:`animedex.api._dispatch`.

Covers the full envelope assembly: pre-call URL/header composition,
rate-limit timing capture, cache lookup + write, HTTP execution
including the redirect chain, body decoding, and final RawResponse
construction.
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


class TestMethodPassThrough:
    @responses.activate
    def test_delete_is_sent_to_upstream(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(responses.DELETE, "https://graphql.anilist.co/", body="", status=204)

        raw = call(backend="anilist", path="/", method="DELETE", cache=cache)

        assert raw.firewall_rejected is None
        assert raw.status == 204
        assert raw.body_bytes == b""
        assert raw.request.method == "DELETE"
        assert responses.calls[0].request.method == "DELETE"


class TestLocalRejection:
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

    @responses.activate
    def test_mutating_looking_methods_bypass_cache(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(responses.DELETE, "https://graphql.anilist.co/", json={"n": 1}, status=200)
        responses.add(responses.DELETE, "https://graphql.anilist.co/", json={"n": 2}, status=200)

        first = call(backend="anilist", path="/", method="DELETE", cache=cache)
        second = call(backend="anilist", path="/", method="DELETE", cache=cache)

        assert first.cache.hit is False
        assert second.cache.hit is False
        assert first.cache.key is None
        assert second.cache.key is None
        assert len(responses.calls) == 2
        assert '"n": 2' in second.body_text


class TestRequestSnapshotRedaction:
    @responses.activate
    def test_authorization_header_is_redacted(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        raw = call(
            backend="jikan",
            path="/anime/52991",
            # 30-char token so the fingerprint form fires (threshold is 24).
            headers={"Authorization": "Bearer aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            cache=cache,
        )

        # The on-the-wire Authorization header was sent (responses
        # captures the actual outgoing headers in responses.calls), but
        # the envelope's request.headers must NOT contain the raw
        # value.
        assert "aaaaaaaaaaaaaaaaaaaaaa" not in raw.request.headers["Authorization"]
        assert raw.request.headers["Authorization"].startswith("Bearer ")
        assert "(len=" in raw.request.headers["Authorization"]


class TestResponseHeaderRedaction:
    """Per review M3: response_headers must be redacted at every site
    where they enter a :class:`RawResponse` envelope. Same vector as M1
    (Shikimori's ``__ddg9_=<client-IP>`` cookie) but at runtime
    instead of in checked-in fixtures.
    """

    @responses.activate
    def test_set_cookie_in_live_envelope_is_redacted(self, fake_clock, cache):
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {}},
            status=200,
            headers={"Set-Cookie": "session=abcd1234567890XYZabcd1234XYZ99; ddg=198.51.100.99"},
        )

        raw = call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True)

        assert "1234567890" not in raw.response_headers["Set-Cookie"]
        assert "198.51.100.99" not in raw.response_headers["Set-Cookie"]

    @responses.activate
    def test_authorization_echo_in_live_envelope_is_redacted(self, fake_clock, cache):
        from animedex.api._dispatch import call

        # Some upstreams echo Authorization back in response headers.
        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={},
            status=200,
            headers={"Authorization": "Bearer abcd1234567890XYZabcd1234XYZ99"},
        )

        raw = call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True)

        assert "1234567890" not in raw.response_headers["Authorization"]

    @responses.activate
    def test_set_cookie_in_cache_write_is_redacted(self, fake_clock, cache):
        """The redaction must happen before the cache row is written;
        otherwise an attacker reading the SQLite file sees raw
        Set-Cookie."""
        from animedex.api._dispatch import call

        responses.add(
            responses.GET,
            "https://api.jikan.moe/v4/anime/52991",
            json={"data": {}},
            status=200,
            headers={"Set-Cookie": "session=abcd1234567890XYZabcd1234XYZ99"},
        )

        # Write to cache.
        call(backend="jikan", path="/anime/52991", cache=cache)

        # Read raw row out of cache to verify what was written.
        from animedex.api._dispatch import _signature

        sig = _signature("GET", "https://api.jikan.moe/v4/anime/52991", None, None, None)
        hit = cache.get_with_meta("jikan", sig)
        assert hit is not None
        _, hdrs, _ = hit
        assert "1234567890" not in hdrs.get("Set-Cookie", "")

    @responses.activate
    def test_set_cookie_on_cache_hit_path_is_redacted(self, fake_clock, cache):
        """Even if the cache row was written before this fix landed,
        the cache-hit reconstruction path must still emit a redacted
        envelope."""
        from animedex.api._dispatch import _signature

        # Manually plant a cache row with un-redacted Set-Cookie (the
        # legacy state).
        sig = _signature("GET", "https://api.jikan.moe/v4/anime/52991", None, None, None)
        cache.set_with_meta(
            "jikan",
            sig,
            b'{"data":{}}',
            response_headers={"Set-Cookie": "session=abcd1234567890XYZabcd1234XYZ99; ddg=198.51.100.99"},
            ttl_seconds=3600,
        )

        from animedex.api._dispatch import call

        raw = call(backend="jikan", path="/anime/52991", cache=cache)

        assert raw.cache.hit is True
        assert "1234567890" not in raw.response_headers["Set-Cookie"]
        assert "198.51.100.99" not in raw.response_headers["Set-Cookie"]


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


class TestConfigThreading:
    """Per review m3: ``_dispatch.call`` must accept
    ``config: Optional[Config] = None`` as lowest-priority defaults so
    that downstream Python users get the documented surface from
    ``plans/05 §4``. Explicit kwargs always win over ``config``.
    """

    @responses.activate
    def test_config_user_agent_used_when_kwarg_absent(self, fake_clock, cache):
        from animedex.api._dispatch import call
        from animedex.config import Config

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        cfg = Config(user_agent="my-bot/9.9 (+contact)")
        raw = call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True, config=cfg)

        # The on-the-wire request used the config's UA.
        sent_ua = responses.calls[-1].request.headers.get("User-Agent", "")
        assert sent_ua == "my-bot/9.9 (+contact)"
        # And the request snapshot reflects the same.
        assert raw.request.headers["User-Agent"] == "my-bot/9.9 (+contact)"

    @responses.activate
    def test_explicit_user_agent_overrides_config(self, fake_clock, cache):
        from animedex.api._dispatch import call
        from animedex.config import Config

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        cfg = Config(user_agent="config-ua/1.0")
        raw = call(
            backend="jikan",
            path="/anime/52991",
            cache=cache,
            no_cache=True,
            user_agent="kwarg-ua/2.0",
            config=cfg,
        )

        assert raw.request.headers["User-Agent"] == "kwarg-ua/2.0"

    @responses.activate
    def test_config_timeout_seconds_used_when_kwarg_absent(self, fake_clock, cache, monkeypatch):
        """Config.timeout_seconds becomes the dispatcher's effective
        timeout when the kwarg is None."""
        from animedex.api._dispatch import call
        from animedex.config import Config

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        captured = {}
        import requests as _r

        original = _r.Session.request

        def _rec(self, *a, **kw):
            captured["timeout"] = kw.get("timeout")
            return original(self, *a, **kw)

        monkeypatch.setattr(_r.Session, "request", _rec)

        cfg = Config(timeout_seconds=7.5)
        call(backend="jikan", path="/anime/52991", cache=cache, no_cache=True, config=cfg)

        assert captured["timeout"] == 7.5

    @responses.activate
    def test_config_cache_ttl_used_when_kwarg_absent(self, fake_clock, cache):
        """Config.cache_ttl_seconds becomes the cache write TTL when
        the kwarg is None."""
        from animedex.api._dispatch import _signature, call
        from animedex.config import Config

        responses.add(responses.GET, "https://api.jikan.moe/v4/anime/52991", json={}, status=200)

        cfg = Config(cache_ttl_seconds=42)
        call(backend="jikan", path="/anime/52991", cache=cache, config=cfg)

        # Read TTL bookkeeping straight from the SQLite row (the cache
        # API doesn't expose the raw expires_at). Dispatcher writes
        # expires_at = fetched_at + ttl_seconds, so the difference
        # equals the configured TTL.
        sig = _signature("GET", "https://api.jikan.moe/v4/anime/52991", None, None, None)
        with cache._lock:
            row = cache._conn.execute(
                "SELECT expires_at, fetched_at FROM cache_rows WHERE backend=? AND signature=?",
                ("jikan", sig),
            ).fetchone()
        assert row is not None
        ttl_written = row[0] - row[1]
        assert ttl_written == 42


class TestSignatureCanonicalisation:
    """Per review m1: cache-key signature must be invariant to the
    order of multi-value query parameters. MangaDex
    ``includes[]=cover_art&includes[]=author`` and
    ``includes[]=author&includes[]=cover_art`` are semantically
    identical to upstream but were producing different signatures.
    """

    def test_list_params_order_invariant(self):
        from animedex.api._dispatch import _signature

        a = _signature(
            "GET",
            "https://api.mangadex.org/manga",
            {"includes[]": ["cover_art", "author"]},
            None,
            None,
        )
        b = _signature(
            "GET",
            "https://api.mangadex.org/manga",
            {"includes[]": ["author", "cover_art"]},
            None,
            None,
        )
        assert a == b

    def test_dict_keys_order_invariant(self):
        from animedex.api._dispatch import _signature

        a = _signature("GET", "https://x.invalid/", {"a": 1, "b": 2}, None, None)
        b = _signature("GET", "https://x.invalid/", {"b": 2, "a": 1}, None, None)
        assert a == b

    def test_json_body_list_order_remains_significant(self):
        """JSON-body lists are NOT canonicalised: REST mutation bodies
        often carry ordered semantics (e.g. ordered relations, page
        cursors). Treating them as sets would risk cache poisoning -
        two semantically different requests sharing a cache key. Only
        query params are canonicalised."""
        from animedex.api._dispatch import _signature

        a = _signature("POST", "https://x.invalid/", None, {"ids": [1, 3, 2]}, None)
        b = _signature("POST", "https://x.invalid/", None, {"ids": [3, 2, 1]}, None)
        assert a != b

    def test_distinct_param_values_still_differ(self):
        """Canonicalisation must not collapse genuinely different
        requests."""
        from animedex.api._dispatch import _signature

        a = _signature("GET", "https://x.invalid/", {"q": "a"}, None, None)
        b = _signature("GET", "https://x.invalid/", {"q": "b"}, None, None)
        assert a != b
