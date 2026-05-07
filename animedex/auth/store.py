"""
:class:`TokenStore` Protocol.

The Protocol enumerates the only operations a backend module needs
on a credential store: store, look up, delete, and enumerate. By
keeping the surface this small we make every backend trivial to
test (with :class:`~animedex.auth.inmemory_store.InMemoryTokenStore`)
and trivial to retarget (e.g. an encrypted-file store for headless
CI, a remote vault for hosted deployments).
"""

from __future__ import annotations

from typing import Iterable, Optional, Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """The Protocol every token-store backend implements.

    All methods are synchronous; the substrate is sync-first per
    ``plans/05 §5``.
    """

    def set(self, backend: str, token: str) -> None:
        """Store the credential for ``backend``, overwriting any prior value.

        :param backend: Backend identifier (e.g. ``"anilist"``).
        :type backend: str
        :param token: Credential text.
        :type token: str
        :return: ``None``.
        :rtype: None
        """
        ...

    def get(self, backend: str) -> Optional[str]:
        """Return the credential for ``backend``, or ``None`` if absent.

        :param backend: Backend identifier.
        :type backend: str
        :return: Token text or ``None``.
        :rtype: str or None
        """
        ...

    def delete(self, backend: str) -> None:
        """Remove the credential for ``backend`` if present.

        Idempotent: deleting a missing entry is not an error.

        :param backend: Backend identifier.
        :type backend: str
        :return: ``None``.
        :rtype: None
        """
        ...

    def keys(self) -> Iterable[str]:
        """Enumerate the backend identifiers that currently have a token.

        :return: Iterable of backend identifiers.
        :rtype: Iterable[str]
        """
        ...
