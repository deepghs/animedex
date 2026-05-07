"""
Programmatic configuration object for animedex callers.

:class:`Config` is the typed, immutable equivalent of the CLI's flag
stack. Every public API function in :mod:`animedex` accepts an
optional ``config`` keyword argument and falls back to module-level
defaults when not given. The CLI translates flags into a
:class:`Config` instance one-to-one and hands it off; downstream
Python users construct a :class:`Config` directly.

The fields here are deliberately a 1:1 mirror of the CLI flags
defined in ``plans/03 §9`` so that "what does this command do" and
"what does this Python call do" stay in lock-step.
"""

from __future__ import annotations

from typing import Optional

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python <3.8 not supported
    from typing_extensions import Literal  # type: ignore

from pydantic import BaseModel, ConfigDict

from animedex.auth.store import TokenStore


_RateLiteral = Literal["normal", "slow"]


class Config(BaseModel):
    """Frozen configuration object.

    :ivar rate: Voluntary rate-limit slowdown. ``"slow"`` halves the
                 default refill rate; ``"normal"`` is the upstream-
                 sanctioned default. We do not expose a faster mode
                 because that would violate P1 caps.
    :vartype rate: Literal["normal", "slow"]
    :ivar cache_ttl_seconds: Override for the per-row TTL applied to
                              new cache entries. ``None`` means each
                              call uses the default for its category.
    :vartype cache_ttl_seconds: int or None
    :ivar no_cache: When ``True`` the call bypasses the cache for
                     both reads and writes.
    :vartype no_cache: bool
    :ivar source_attribution: When ``True`` (the default) the JSON
                                renderer includes ``_source`` on
                                every field. The TTY renderer always
                                shows the source column.
    :vartype source_attribution: bool
    :ivar user_agent: Override for the User-Agent string. ``None``
                       means the project default
                       (:func:`animedex.transport.useragent.default_user_agent`).
    :vartype user_agent: str or None
    :ivar timeout_seconds: HTTP request timeout in seconds.
    :vartype timeout_seconds: float
    :ivar token_store: Caller-supplied
                        :class:`~animedex.auth.store.TokenStore`.
                        ``None`` means resolve lazily to a
                        :class:`~animedex.auth.keyring_store.KeyringTokenStore`
                        on first use.
    :vartype token_store: TokenStore or None
    """

    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    rate: _RateLiteral = "normal"
    cache_ttl_seconds: Optional[int] = None
    no_cache: bool = False
    source_attribution: bool = True
    user_agent: Optional[str] = None
    timeout_seconds: float = 30.0
    token_store: Optional[TokenStore] = None

    def effective_token_store(self) -> TokenStore:
        """Resolve :attr:`token_store` to a usable
        :class:`~animedex.auth.store.TokenStore`.

        Returns the explicitly-supplied store when one was passed,
        otherwise constructs a fresh
        :class:`~animedex.auth.keyring_store.KeyringTokenStore`. The
        construction is deferred to call time so an environment
        without a real OS keyring backend does not break a code path
        that never actually needs credentials.

        :return: A :class:`TokenStore` ready for use.
        :rtype: TokenStore
        """
        if self.token_store is not None:
            return self.token_store
        from animedex.auth.keyring_store import KeyringTokenStore

        return KeyringTokenStore()


def selftest() -> bool:
    """Smoke-test the :class:`Config` object.

    Constructs the zero-arg default and a fully-populated instance,
    verifies the rate literal validation, and resolves the default
    token store; all of this stays in process memory.

    :return: ``True`` on success.
    :rtype: bool
    """
    cfg = Config()
    assert cfg.rate == "normal"
    full = Config(
        rate="slow",
        cache_ttl_seconds=10,
        no_cache=True,
        source_attribution=False,
        user_agent="x/1",
        timeout_seconds=5.0,
    )
    assert full.timeout_seconds == 5.0
    cfg.effective_token_store()
    return True
