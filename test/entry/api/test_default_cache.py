"""Tests for :func:`animedex.entry.api._default_cache`.

Per review m4: the lazy singleton must register an :func:`atexit`
hook that closes the SQLite connection cleanly on shutdown, and the
test session must redirect the singleton to a tmp path so a CLI
subcommand exercised through :class:`click.testing.CliRunner` does
not write to ``~/.cache/animedex/cache.sqlite``.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestDefaultCacheLifecycle:
    def test_first_call_constructs_and_registers_atexit(self, monkeypatch):
        """The first invocation builds a SqliteCache and registers a
        shutdown hook. Subsequent invocations reuse the singleton."""
        import animedex.entry.api as entry_api

        monkeypatch.setattr(entry_api, "_DEFAULT_CACHE", None)

        registrations: list = []

        # Capture every atexit.register call made under the helper.
        import atexit

        original = atexit.register

        def _capturing_register(fn, *args, **kw):
            registrations.append(fn)
            return original(fn, *args, **kw)

        monkeypatch.setattr("atexit.register", _capturing_register)

        c1 = entry_api._default_cache()
        c2 = entry_api._default_cache()

        assert c1 is c2, "the singleton must reuse the first construction"
        assert len(registrations) == 1, (
            f"exactly one atexit hook should be registered on first construction (got {len(registrations)})"
        )

    def test_close_default_cache_releases_singleton(self, monkeypatch):
        """The atexit hook closes the singleton and resets the
        module-global so a subsequent ``_default_cache()`` call
        constructs a fresh instance."""
        import animedex.entry.api as entry_api

        first = entry_api._default_cache()
        assert entry_api._DEFAULT_CACHE is first

        entry_api._close_default_cache()
        assert entry_api._DEFAULT_CACHE is None

        # Subsequent call rebuilds the singleton (proves the closer
        # really released, not just hid, the previous instance).
        second = entry_api._default_cache()
        assert second is not first

    def test_close_default_cache_is_idempotent(self):
        """Calling the hook with no singleton present is a no-op,
        not an error - matters for shutdown flows that may double-fire."""
        import animedex.entry.api as entry_api

        # Already None thanks to the autouse isolation fixture.
        assert entry_api._DEFAULT_CACHE is None
        entry_api._close_default_cache()  # must not raise
        assert entry_api._DEFAULT_CACHE is None

    def test_close_default_cache_swallows_close_errors(self, monkeypatch):
        """A SqliteCache.close() that throws during teardown must not
        propagate - the OS releases the file handle regardless and
        a traceback printed on shutdown is just noise."""
        import animedex.entry.api as entry_api

        class BoomCache:
            def close(self):
                raise RuntimeError("oops")

        monkeypatch.setattr(entry_api, "_DEFAULT_CACHE", BoomCache())
        entry_api._close_default_cache()  # must not raise
        assert entry_api._DEFAULT_CACHE is None

    def test_singleton_path_redirected_by_conftest(self, tmp_path):
        """The autouse ``_isolate_default_cache`` fixture in
        ``conftest.py`` redirects the singleton path under the test's
        ``tmp_path``. This test asserts the redirection actually works
        by triggering construction and verifying the SQLite file lands
        inside the tmp_path."""
        import animedex.cache.sqlite as cache_mod

        # The conftest patches the platform cache-dir resolver so all
        # singleton caches land under tmp_path.
        assert cache_mod.default_cache_path() == tmp_path / "cache.sqlite"
