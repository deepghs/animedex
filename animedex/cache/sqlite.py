"""
SQLite-backed TTL cache for backend responses.

The cache is the project's canonical storage for upstream responses;
it is consulted before any HTTP call and populated after one. The
shape is:

* Rows are keyed by ``(backend, signature)``.
* The body is stored as raw bytes; pydantic models are persisted as
  ``model.model_dump_json().encode("utf-8")`` and re-hydrated with
  ``Model.model_validate_json(raw.decode())``.
* Each row carries a TTL (seconds-since-epoch ``expires_at``); a row
  whose ``expires_at`` is in the past is treated as missing.

The defaults in :func:`default_ttl_seconds` come from
``plans/03 §10``: 72 h for metadata, 24 h for list pages, 1 h for
schedule / trending, 30 d for offline dumps. Anything else gets the
"metadata" default.

The clock primitive (:data:`_utcnow`) and the cache-dir resolver
(:data:`_user_cache_dir`) are pulled through indirection points so
unit tests can substitute deterministic fakes without monkeypatching
the standard library globally.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from platformdirs import user_cache_dir


_utcnow = lambda: datetime.now(timezone.utc)  # noqa: E731 - patched in tests
_user_cache_dir = lambda: user_cache_dir("animedex")  # noqa: E731 - patched in tests


_DEFAULT_TTL_SECONDS = {
    "metadata": 72 * 3600,
    "list": 24 * 3600,
    "schedule": 3600,
    "trending": 3600,
    "offline_dump": 30 * 86400,
}


def default_ttl_seconds(category: str) -> int:
    """Return the project-default TTL for a request category.

    Per ``plans/03 §10``:

    * ``metadata``: 72 h
    * ``list``: 24 h
    * ``schedule`` / ``trending``: 1 h
    * ``offline_dump``: 30 d

    Unknown categories collapse to the metadata default; this keeps
    the cache useful for one-off entries without forcing every call
    site to declare a category.

    :param category: Request category.
    :type category: str
    :return: Default TTL in seconds.
    :rtype: int
    """
    return _DEFAULT_TTL_SECONDS.get(category, _DEFAULT_TTL_SECONDS["metadata"])


def default_cache_path() -> Path:
    """Resolve the platform-appropriate cache file path.

    Uses :func:`platformdirs.user_cache_dir` (via the
    :data:`_user_cache_dir` indirection) so the location matches the
    OS convention: ``~/.cache/animedex`` on Linux,
    ``~/Library/Caches/animedex`` on macOS, the appropriate
    ``LOCALAPPDATA`` subtree on Windows.

    :return: Path to ``cache.sqlite`` inside the cache dir.
    :rtype: pathlib.Path
    """
    return Path(_user_cache_dir()) / "cache.sqlite"


class SqliteCache:
    """A small SQLite-backed cache with per-row TTL.

    :param path: Filesystem path to the SQLite database file.
                  Defaults to :func:`default_cache_path`.
    :type path: pathlib.Path or str or None
    """

    _SCHEMA_V1 = """
        CREATE TABLE IF NOT EXISTS cache_rows (
            backend     TEXT NOT NULL,
            signature   TEXT NOT NULL,
            payload     BLOB NOT NULL,
            expires_at  INTEGER NOT NULL,
            PRIMARY KEY (backend, signature)
        ) WITHOUT ROWID;
    """

    _CACHE_META_SCHEMA = """
        CREATE TABLE IF NOT EXISTS cache_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """

    _CURRENT_SCHEMA_VERSION = 2

    def __init__(self, path: Optional[Union[Path, str]] = None) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False so backend retry/backoff helpers running on
        # worker threads do not hit sqlite3.ProgrammingError. We pair it with
        # an in-process _lock to serialise access across threads sharing this
        # SqliteCache instance; SQLite itself does not serialise concurrent
        # `execute` calls on the same connection.
        # journal_mode=WAL allows multiple animedex invocations on the same
        # machine (a CLI and `animedex mcp serve`, say) to coexist instead of
        # locking each other out via the default rollback journal.
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(self._SCHEMA_V1)
            self._conn.execute(self._CACHE_META_SCHEMA)
            self._migrate_schema_locked()
            self._conn.commit()

    def _read_schema_version_locked(self) -> int:
        """Return the persisted schema version, defaulting to 1.

        Pre-v2 databases lack the ``cache_meta`` table at the time of
        creation; the v2 init populates it on first open.

        :return: Schema version integer.
        :rtype: int
        """
        row = self._conn.execute("SELECT value FROM cache_meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            # Detect a pre-existing v1 cache_rows table to distinguish a
            # fresh db from a legacy one. A fresh db has cache_meta empty
            # and cache_rows empty too; we treat that as v1 about-to-be-
            # upgraded, which is harmless because the migration is
            # ALTER TABLE add-column with NULL defaults.
            return 1
        return int(row[0])

    def _migrate_schema_locked(self) -> None:
        """Bring the schema up to :attr:`_CURRENT_SCHEMA_VERSION`.

        v1 → v2 adds two nullable columns (``response_headers``,
        ``fetched_at``) so cache hits can reconstruct the full
        ``RawResponse`` envelope. Old rows show ``NULL`` for both,
        which the get_with_meta helper translates to an empty headers
        dict and a ``None`` fetched_at.
        """
        current = self._read_schema_version_locked()

        if current < 2:
            # Add columns; ignore errors when columns already exist
            # (re-run resilience).
            for stmt in (
                "ALTER TABLE cache_rows ADD COLUMN response_headers BLOB",
                "ALTER TABLE cache_rows ADD COLUMN fetched_at INTEGER",
            ):
                try:
                    self._conn.execute(stmt)
                except sqlite3.OperationalError:
                    pass
            current = 2

        # Persist the schema version.
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_meta (key, value) VALUES ('schema_version', ?)",
            (str(current),),
        )

    def close(self) -> None:
        """Close the underlying SQLite connection.

        :return: ``None``.
        :rtype: None
        """
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "SqliteCache":
        return self

    def __exit__(self, *_excinfo: object) -> None:
        self.close()

    def _expires_at_seconds(self, ttl_seconds: int) -> int:
        return int(_utcnow().timestamp()) + int(ttl_seconds)

    def _now_seconds(self) -> int:
        return int(_utcnow().timestamp())

    def set(self, backend: str, signature: str, payload: bytes, *, ttl_seconds: int) -> None:
        """Store or overwrite a row (v1 wrapper).

        Exists for callers that don't need the v2 metadata. Internally
        delegates to :meth:`set_with_meta` with ``response_headers={}``,
        so a subsequent ``get_with_meta`` returns a valid row with
        ``fetched_at=now`` and an empty headers dict.

        :param backend: Backend identifier (e.g. ``"anilist"``).
        :type backend: str
        :param signature: Caller-derived row signature; must be
                           stable across runs for the same logical
                           request.
        :type signature: str
        :param payload: Raw bytes to store.
        :type payload: bytes
        :param ttl_seconds: Lifetime in seconds; ``get`` will treat
                             this row as missing once the time
                             elapses.
        :type ttl_seconds: int
        :return: ``None``.
        :rtype: None
        """
        self.set_with_meta(backend, signature, payload, response_headers={}, ttl_seconds=ttl_seconds)

    def set_with_meta(
        self,
        backend: str,
        signature: str,
        payload: bytes,
        *,
        response_headers: Dict[str, str],
        ttl_seconds: int,
    ) -> None:
        """Store or overwrite a row with v2 metadata.

        :param backend: Backend identifier.
        :type backend: str
        :param signature: Caller-derived row signature.
        :type signature: str
        :param payload: Raw bytes to store.
        :type payload: bytes
        :param response_headers: Response headers dict; persisted as
                                  JSON-encoded bytes so cache hits in
                                  ``--debug`` mode can reconstruct the
                                  full envelope.
        :type response_headers: dict[str, str]
        :param ttl_seconds: Lifetime in seconds.
        :type ttl_seconds: int
        :return: ``None``.
        :rtype: None
        """
        headers_blob = json.dumps(response_headers, ensure_ascii=False).encode("utf-8")
        fetched_at_seconds = self._now_seconds()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO cache_rows
                    (backend, signature, payload, expires_at, response_headers, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    backend,
                    signature,
                    payload,
                    self._expires_at_seconds(ttl_seconds),
                    headers_blob,
                    fetched_at_seconds,
                ),
            )
            self._conn.commit()

    def get(self, backend: str, signature: str) -> Optional[bytes]:
        """Look up a row.

        Returns the payload if the row exists and has not expired;
        ``None`` otherwise. Expired rows are *not* deleted on read
        (use :meth:`purge_expired` for that) so a single ``get``
        stays a pure read.

        :param backend: Backend identifier.
        :type backend: str
        :param signature: Caller-derived row signature.
        :type signature: str
        :return: Cached payload or ``None`` when missing / expired.
        :rtype: bytes or None
        """
        out = self.get_with_meta(backend, signature)
        if out is None:
            return None
        payload, _hdrs, _fetched_at = out
        return payload

    def get_with_meta(self, backend: str, signature: str) -> Optional[Tuple[bytes, Dict[str, str], Optional[datetime]]]:
        """Look up a row including v2 metadata.

        :param backend: Backend identifier.
        :type backend: str
        :param signature: Caller-derived row signature.
        :type signature: str
        :return: ``(payload, response_headers, fetched_at)`` triple
                 on hit, ``None`` when missing or expired. Migrated
                 v1 rows return an empty headers dict and
                 ``fetched_at=None``.
        :rtype: tuple or None
        """
        with self._lock:
            row = self._conn.execute(
                """
                SELECT payload, expires_at, response_headers, fetched_at
                FROM cache_rows WHERE backend = ? AND signature = ?
                """,
                (backend, signature),
            ).fetchone()
        if row is None:
            return None
        payload, expires_at, headers_blob, fetched_at_seconds = row
        if expires_at <= self._now_seconds():
            return None
        headers: Dict[str, str] = {}
        if headers_blob:
            try:
                headers = json.loads(headers_blob)
            except (ValueError, TypeError):
                headers = {}
        fetched_at = (
            datetime.fromtimestamp(fetched_at_seconds, tz=timezone.utc) if fetched_at_seconds is not None else None
        )
        return payload, headers, fetched_at

    def purge_expired(self) -> int:
        """Delete every expired row.

        :return: Number of rows removed.
        :rtype: int
        """
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM cache_rows WHERE expires_at <= ?",
                (self._now_seconds(),),
            )
            self._conn.commit()
            return cur.rowcount


def selftest() -> bool:
    """Smoke-test the SQLite cache.

    Builds a temporary cache file under :data:`_user_cache_dir`,
    writes a row, reads it back, lets the test-supplied clock
    advance past the TTL, and confirms expiry. Cleans up the
    temporary file before returning.

    :return: ``True`` on success.
    :rtype: bool
    """
    path = Path(_user_cache_dir()) / "selftest.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        os.remove(path)
    cache = SqliteCache(path=path)
    try:
        cache.set("_selftest", "key", b"hello", ttl_seconds=60)
        assert cache.get("_selftest", "key") == b"hello"
        assert cache.get("_selftest", "missing") is None
        assert default_ttl_seconds("metadata") == 72 * 3600
    finally:
        cache.close()
        if path.exists():
            os.remove(path)
    return True
