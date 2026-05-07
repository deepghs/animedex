"""
OS-keyring implementation of :class:`~animedex.auth.store.TokenStore`.

Per ``plans/02 §7`` this is the production token store: tokens live
in the OS keyring (Secret Service on Linux, Keychain on macOS,
Credential Locker on Windows) so a stolen dotfile cannot exfiltrate
credentials. Enumeration (:meth:`keys`) is the one operation the
``keyring`` package does not expose uniformly; we keep an in-process
companion set populated as :meth:`set` and :meth:`delete` are called,
so :meth:`keys` returns what *this process* has registered. CLI
callers that need the full host-wide list use the OS keyring viewer.

Tests never touch the real keyring; the module pulls
:data:`_keyring` through an indirection so a fake module can be
swapped in.
"""

from __future__ import annotations

import keyring as _keyring
from typing import Iterable, Optional


_DEFAULT_SERVICE = "animedex"


class KeyringTokenStore:
    """A :class:`~animedex.auth.store.TokenStore` backed by the OS keyring.

    :param service: Keyring service namespace under which entries
                     live; defaults to ``"animedex"``. Test code
                     overrides this so production keyring entries
                     stay untouched.
    :type service: str
    """

    def __init__(self, *, service: str = _DEFAULT_SERVICE) -> None:
        self._service = service
        self._known_keys: set = set()

    def set(self, backend: str, token: str) -> None:
        _keyring.set_password(self._service, backend, token)
        self._known_keys.add(backend)

    def get(self, backend: str) -> Optional[str]:
        return _keyring.get_password(self._service, backend)

    def delete(self, backend: str) -> None:
        _keyring.delete_password(self._service, backend)
        self._known_keys.discard(backend)

    def keys(self) -> Iterable[str]:
        return list(self._known_keys)


def selftest() -> bool:
    """Smoke-test the keyring store at the import level only.

    Per ``plans/02 §7`` and ``plans/04 §2`` this selftest *must not*
    touch the real OS keyring: a CI environment may have no backend
    available, and writing a real entry from the diagnostic would be
    a side effect users do not expect.

    The function therefore only verifies that the ``keyring``
    package imports and exposes the three call sites the store
    relies on. The behaviour itself is exercised in unit tests via
    a faked module.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert callable(getattr(_keyring, "set_password", None))
    assert callable(getattr(_keyring, "get_password", None))
    assert callable(getattr(_keyring, "delete_password", None))
    return True
