"""Pytest configuration shared across the test tree.

The structure under ``test/`` mirrors ``animedex/`` exactly so that
``make unittest RANGE_DIR=<path>`` covers both source and matching
tests in a single invocation.

Per review m4: every test session runs with the API-layer
:data:`animedex.entry.api._DEFAULT_CACHE` redirected to a temporary
path. Otherwise a CLI subcommand exercised through
:class:`click.testing.CliRunner` would create
``~/.cache/animedex/cache.sqlite`` on the contributor's machine (and
on CI runners) on first use.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_default_cache(tmp_path, monkeypatch):
    """Redirect the API-layer default cache singleton to a tmp path.

    Active for every test, no opt-in needed: the cost is negligible
    (the singleton is lazy, so the redirected path is only used when
    the test actually hits a CLI subcommand that constructs a cache),
    and the safety bound prevents a forgotten ``--no-cache`` flag in
    a new test from polluting the contributor's home directory.

    Resets cache-owning module globals to ``None`` and monkeypatches
    the platform-default directory resolver so that any first-use
    construction lands inside ``tmp_path``.
    """
    import animedex.cache.sqlite as _cache_mod
    import animedex.backends.quote as _quote_api
    import animedex.backends.shikimori as _shikimori_api
    import animedex.entry.api as _entry_api

    monkeypatch.setattr(_quote_api, "_DEFAULT_CACHE", None)
    monkeypatch.setattr(_shikimori_api, "_DEFAULT_CACHE", None)
    monkeypatch.setattr(_entry_api, "_DEFAULT_CACHE", None)
    monkeypatch.setattr(_cache_mod, "_user_cache_dir", lambda: str(tmp_path))
    yield


@pytest.fixture
def assert_no_cache_in_home():
    """Helper for tests that exercise CLI cache flow: assert nothing
    landed at ``~/.cache/animedex/`` during the test body."""
    from pathlib import Path

    sentinel = Path.home() / ".cache" / "animedex" / "cache.sqlite"
    pre_existed = sentinel.exists()
    pre_mtime = sentinel.stat().st_mtime if pre_existed else None
    yield
    if not pre_existed:
        assert not sentinel.exists(), f"Test created {sentinel} - the conftest cache-isolation fixture is broken"
    else:
        assert sentinel.stat().st_mtime == pre_mtime, (
            f"Test mutated {sentinel} - the conftest cache-isolation fixture is broken"
        )
