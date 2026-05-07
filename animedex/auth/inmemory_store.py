"""
In-memory implementation of :class:`~animedex.auth.store.TokenStore`.

Used in two places: by unit tests (so credential paths are
exercisable without OS-level state), and by callers running in a
headless CI environment where the real keyring has no backend
(``plans/02 §7`` rules out plain-text disk fallbacks; this in-memory
store is the documented escape hatch for ephemeral processes).
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional


class InMemoryTokenStore:
    """A :class:`~animedex.auth.store.TokenStore` that lives in process memory.

    :param initial: Optional pre-populated mapping. Useful for tests
                     that want to assert authenticated behaviour
                     without dispatching through the real keyring.
    :type initial: Mapping[str, str] or None
    """

    def __init__(self, initial: Optional[Mapping[str, str]] = None) -> None:
        self._storage: Dict[str, str] = dict(initial) if initial else {}

    def set(self, backend: str, token: str) -> None:
        self._storage[backend] = token

    def get(self, backend: str) -> Optional[str]:
        return self._storage.get(backend)

    def delete(self, backend: str) -> None:
        self._storage.pop(backend, None)

    def keys(self) -> Iterable[str]:
        return list(self._storage.keys())


def selftest() -> bool:
    """Smoke-test the in-memory store.

    Round-trips a value, deletes it, confirms the deletion is
    idempotent, and confirms an absent key reads as ``None``.

    :return: ``True`` on success.
    :rtype: bool
    """
    store = InMemoryTokenStore()
    store.set("_selftest", "value")
    assert store.get("_selftest") == "value"
    store.delete("_selftest")
    store.delete("_selftest")  # idempotent
    assert store.get("_selftest") is None
    InMemoryTokenStore({"a": "b"}).get("a") == "b"
    return True
