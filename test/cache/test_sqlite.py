"""
Tests for :mod:`animedex.cache.sqlite`.

The cache must round-trip pydantic-shaped payloads, honour per-row
TTL, expose a default per-backend / per-category TTL table, expire
rows once their TTL elapses, and keep keying stable so a re-run
finds the same row. The tests pin those properties using a
monkeypatched clock so expiry is deterministic.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    """Drive :data:`animedex.cache.sqlite._utcnow` from the test."""
    from datetime import datetime, timezone

    state = {"now": datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)}

    def now():
        return state["now"]

    monkeypatch.setattr("animedex.cache.sqlite._utcnow", now)
    state["advance"] = lambda secs: state.update(
        now=state["now"].__class__.fromtimestamp(state["now"].timestamp() + secs, tz=timezone.utc)
    )
    return state


@pytest.fixture
def cache(tmp_path):
    from animedex.cache.sqlite import SqliteCache

    return SqliteCache(path=tmp_path / "test-cache.sqlite")


class TestRoundTrip:
    def test_set_then_get(self, cache, fake_clock):
        cache.set("anilist", "sig:1", b'{"a":1}', ttl_seconds=60)
        out = cache.get("anilist", "sig:1")
        assert out == b'{"a":1}'

    def test_get_missing_returns_none(self, cache, fake_clock):
        assert cache.get("anilist", "sig:nonexistent") is None

    def test_set_overwrites_previous(self, cache, fake_clock):
        cache.set("anilist", "sig:1", b'{"a":1}', ttl_seconds=60)
        cache.set("anilist", "sig:1", b'{"a":2}', ttl_seconds=60)
        assert cache.get("anilist", "sig:1") == b'{"a":2}'


class TestExpiry:
    def test_expired_row_returns_none(self, cache, fake_clock):
        cache.set("anilist", "sig:1", b"x", ttl_seconds=60)
        fake_clock["advance"](120)
        assert cache.get("anilist", "sig:1") is None

    def test_unexpired_row_returns_value(self, cache, fake_clock):
        cache.set("anilist", "sig:1", b"x", ttl_seconds=60)
        fake_clock["advance"](30)
        assert cache.get("anilist", "sig:1") == b"x"

    def test_purge_expired_removes_rows(self, cache, fake_clock):
        cache.set("anilist", "sig:1", b"x", ttl_seconds=60)
        cache.set("anilist", "sig:2", b"y", ttl_seconds=60)
        fake_clock["advance"](120)
        removed = cache.purge_expired()
        assert removed == 2


class TestKeying:
    def test_keys_isolated_per_backend(self, cache, fake_clock):
        cache.set("anilist", "shared", b"a", ttl_seconds=60)
        cache.set("jikan", "shared", b"b", ttl_seconds=60)
        assert cache.get("anilist", "shared") == b"a"
        assert cache.get("jikan", "shared") == b"b"


class TestDefaultTTL:
    def test_known_categories(self):
        from animedex.cache.sqlite import default_ttl_seconds

        assert default_ttl_seconds("metadata") == 72 * 3600
        assert default_ttl_seconds("list") == 24 * 3600
        assert default_ttl_seconds("schedule") == 3600
        assert default_ttl_seconds("offline_dump") == 30 * 86400

    def test_unknown_category_returns_default(self):
        from animedex.cache.sqlite import default_ttl_seconds

        assert default_ttl_seconds("unknown-category") > 0


class TestPydanticRoundTrip:
    def test_round_trip_via_model_dump_json(self, cache, fake_clock):
        from datetime import datetime, timezone

        from animedex.models.anime import Anime, AnimeTitle
        from animedex.models.common import SourceTag

        original = Anime(
            id="anilist:154587",
            title=AnimeTitle(romaji="Frieren"),
            ids={"mal": "52991"},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )

        cache.set("anilist", "anime:154587", original.model_dump_json().encode("utf-8"), ttl_seconds=60)
        raw = cache.get("anilist", "anime:154587")

        rt = Anime.model_validate_json(raw.decode("utf-8"))
        assert rt == original


class TestPathResolution:
    def test_default_path_uses_platformdirs(self, monkeypatch, tmp_path):
        monkeypatch.setattr("animedex.cache.sqlite._user_cache_dir", lambda: str(tmp_path))
        from animedex.cache.sqlite import default_cache_path

        path = default_cache_path()
        assert str(path).startswith(str(tmp_path))


class TestConcurrency:
    def test_threaded_access_does_not_raise(self, tmp_path):
        """A worker thread accessing the cache must not hit
        ``sqlite3.ProgrammingError`` from the default
        ``check_same_thread=True``."""
        import threading

        from animedex.cache.sqlite import SqliteCache

        cache = SqliteCache(path=tmp_path / "thread.sqlite")
        errors = []

        def worker(i):
            try:
                cache.set("anilist", f"k{i}", b"v", ttl_seconds=60)
                assert cache.get("anilist", f"k{i}") == b"v"
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"thread errors: {errors!r}"

    def test_two_connections_on_same_path_coexist(self, tmp_path):
        """A second :class:`SqliteCache` on the same path must read
        what the first wrote without locking it out (WAL mode)."""
        from animedex.cache.sqlite import SqliteCache

        path = tmp_path / "shared.sqlite"
        a = SqliteCache(path=path)
        try:
            a.set("anilist", "k", b"hello", ttl_seconds=60)
            b = SqliteCache(path=path)
            try:
                assert b.get("anilist", "k") == b"hello"
            finally:
                b.close()
        finally:
            a.close()


class TestContextManager:
    def test_with_block_closes(self, tmp_path):
        from animedex.cache.sqlite import SqliteCache

        with SqliteCache(path=tmp_path / "ctx-cache.sqlite") as c:
            c.set("anilist", "k", b"v", ttl_seconds=60)
        # The connection should be closed; a second open should still
        # see the row durably.
        with SqliteCache(path=tmp_path / "ctx-cache.sqlite") as c2:
            assert c2.get("anilist", "k") == b"v"


class TestSelftest:
    def test_selftest_runs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("animedex.cache.sqlite._user_cache_dir", lambda: str(tmp_path))
        from animedex.cache import sqlite

        assert sqlite.selftest() is True

    def test_selftest_idempotent_across_runs(self, tmp_path, monkeypatch):
        """Two consecutive selftest invocations exercise the
        ``if path.exists(): os.remove(path)`` cleanup branch."""
        monkeypatch.setattr("animedex.cache.sqlite._user_cache_dir", lambda: str(tmp_path))
        from animedex.cache import sqlite

        assert sqlite.selftest() is True
        assert sqlite.selftest() is True
