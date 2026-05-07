"""Coverage tests for the small edge branches inside
:mod:`animedex.cache.sqlite`.

* ``default_cache_path()`` is the public path-derivation function.
* The schema-migration path swallows ``sqlite3.OperationalError`` when
  a v1->v2 ALTER tries to add a column the row already has (re-entry
  resilience).
* ``get_with_meta()`` tolerates a malformed ``response_headers`` blob
  by returning an empty dict rather than raising.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestDefaultCachePath:
    def test_returns_pathlib_path_under_cache_dir(self, monkeypatch, tmp_path):
        """The autouse conftest fixture monkey-patches
        ``default_cache_path`` itself, so to exercise the original
        one-liner we ``monkeypatch.undo()`` first and then re-patch
        ``_user_cache_dir`` (which the original ``default_cache_path``
        delegates to)."""
        from animedex.cache import sqlite as sqlite_mod

        monkeypatch.undo()
        monkeypatch.setattr(sqlite_mod, "_user_cache_dir", lambda: str(tmp_path))
        out = sqlite_mod.default_cache_path()
        assert out.parent == tmp_path
        assert out.name == "cache.sqlite"


class TestSchemaMigrationReentry:
    """When a v1->v2 ALTER fails because the column already exists,
    the migration must catch the error and continue. Otherwise a
    re-opened cache file would crash the second startup."""

    def test_already_v2_schema_does_not_crash(self, tmp_path):
        from animedex.cache.sqlite import SqliteCache

        path = tmp_path / "twice.sqlite"

        cache_a = SqliteCache(path=path)
        cache_a.set_with_meta("jikan", "sig1", b'{"a":1}', response_headers={"X": "y"}, ttl_seconds=60)
        cache_a.close()

        # Re-open the same path. The ``ALTER TABLE ... ADD COLUMN``
        # in _migrate_schema_locked would error with
        # ``duplicate column name`` if not caught; this exercise
        # proves the except path keeps the migration moving.
        cache_b = SqliteCache(path=path)
        hit = cache_b.get_with_meta("jikan", "sig1")
        assert hit is not None
        payload, hdrs, _ = hit
        assert payload == b'{"a":1}'
        assert hdrs == {"X": "y"}
        cache_b.close()

    def test_v1_file_with_columns_already_present_completes_migration(self, tmp_path):
        """Simulate the ragged-shutdown race: a process started v1->
        v2 migration, added the columns, but crashed before stamping
        the schema_version row to '2'. The next open sees v1 in
        cache_meta but finds the columns already exist; the ALTERs
        fail with ``duplicate column name``, the except path
        swallows them, and the migration moves on to stamp '2'.
        """
        import sqlite3

        path = tmp_path / "ragged.sqlite"

        # Manually construct a v1-style schema with the v2 columns
        # already present.
        conn = sqlite3.connect(path)
        conn.executescript(
            """
            CREATE TABLE cache_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO cache_meta (key, value) VALUES ('schema_version', '1');
            CREATE TABLE cache_rows (
                backend TEXT NOT NULL,
                signature TEXT NOT NULL,
                payload BLOB NOT NULL,
                expires_at INTEGER NOT NULL,
                response_headers BLOB,
                fetched_at INTEGER,
                PRIMARY KEY (backend, signature)
            );
            """
        )
        conn.commit()
        conn.close()

        from animedex.cache.sqlite import SqliteCache

        # Re-opening must not raise — the duplicate-column ALTER
        # failures must be swallowed by the except path, and the
        # schema must be stamped at '2' for next time.
        cache = SqliteCache(path=path)
        cache.set_with_meta("jikan", "sig", b"{}", response_headers={}, ttl_seconds=60)
        cache.close()

        conn = sqlite3.connect(path)
        version = conn.execute("SELECT value FROM cache_meta WHERE key = 'schema_version'").fetchone()[0]
        conn.close()
        assert version == "2"


class TestGetWithMetaMalformedHeaders:
    """If a row's ``response_headers`` blob is corrupt JSON (e.g. a
    half-written write that survived a crash), ``get_with_meta``
    must still return the payload with an empty headers dict rather
    than raise."""

    def test_corrupt_headers_blob_yields_empty_dict(self, tmp_path):
        from animedex.cache.sqlite import SqliteCache

        cache = SqliteCache(path=tmp_path / "corrupt.sqlite")
        cache.set_with_meta("jikan", "sig", b"{}", response_headers={"X": "y"}, ttl_seconds=60)

        # Stomp on the response_headers blob with non-JSON.
        with cache._lock:
            cache._conn.execute(
                "UPDATE cache_rows SET response_headers = ? WHERE backend = ? AND signature = ?",
                (b"not-valid-json{{", "jikan", "sig"),
            )
            cache._conn.commit()

        hit = cache.get_with_meta("jikan", "sig")
        assert hit is not None
        payload, hdrs, _ = hit
        assert payload == b"{}"
        assert hdrs == {}

        cache.close()
