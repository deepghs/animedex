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

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

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

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS cache_rows (
            backend     TEXT NOT NULL,
            signature   TEXT NOT NULL,
            payload     BLOB NOT NULL,
            expires_at  INTEGER NOT NULL,
            PRIMARY KEY (backend, signature)
        ) WITHOUT ROWID;
    """

    def __init__(self, path: Optional[Union[Path, str]] = None) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(self._SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection.

        :return: ``None``.
        :rtype: None
        """
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
        """Store or overwrite a row.

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
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_rows (backend, signature, payload, expires_at) VALUES (?, ?, ?, ?)",
            (backend, signature, payload, self._expires_at_seconds(ttl_seconds)),
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
        row = self._conn.execute(
            "SELECT payload, expires_at FROM cache_rows WHERE backend = ? AND signature = ?",
            (backend, signature),
        ).fetchone()
        if row is None:
            return None
        payload, expires_at = row
        if expires_at <= self._now_seconds():
            return None
        return payload

    def purge_expired(self) -> int:
        """Delete every expired row.

        :return: Number of rows removed.
        :rtype: int
        """
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
