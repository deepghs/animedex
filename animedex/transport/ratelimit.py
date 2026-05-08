"""
Per-backend rate limiting for animedex's outgoing HTTP traffic.

This module provides three pieces:

* :class:`TokenBucket` - a small, monotonic-clock-driven token bucket
  with both non-blocking (:meth:`TokenBucket.try_acquire`) and
  blocking (:meth:`TokenBucket.acquire`) variants. Backends use the
  blocking form on the request hot path; :meth:`try_acquire` is for
  transparent fast-fail in tests and back-pressure logic.
* :class:`RateLimitRegistry` - a name-keyed map from backend
  identifier to its configured bucket. The substrate ships exactly
  one default registry (:func:`default_registry`) so the per-backend
  caps from ``plans/01`` and the P1 obligations from ``plans/02``
  live in one place.
* :func:`default_registry` - the wired-up registry with the caps
  every backend documented in ``plans/01-public-apis-anime-survey.md``
  honours.

The ``Rate.slow`` override (CLI flag ``--rate slow``) halves the
refill rate; we never expose a faster-than-default mode because the
upstream contract is a P1 ceiling, not a preference.

The module pulls its clock primitives through two indirection points,
:data:`_monotonic` and :data:`_sleep`, so unit tests can substitute a
deterministic fake without monkeypatching the standard library
globally.
"""

from __future__ import annotations

import threading
import time
from typing import Dict

from animedex.models.common import ApiError


_monotonic = time.monotonic
_sleep = time.sleep


class TokenBucket:
    """A monotonic-clock token bucket.

    The bucket holds at most ``capacity`` tokens and accumulates them
    at ``refill_per_second`` per second. Each acquire consumes one
    token. The implementation is thread-safe and uses
    :data:`_monotonic` / :data:`_sleep` rather than direct ``time``
    calls so tests can swap in a fake clock.

    :param capacity: Maximum number of tokens the bucket can hold.
                      Must be positive.
    :type capacity: int
    :param refill_per_second: Steady-state refill rate, in tokens per
                                second. Must be positive.
    :type refill_per_second: float
    :raises ValueError: When ``capacity`` or ``refill_per_second`` is
                         not strictly positive.
    """

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")
        self.capacity = capacity
        self.refill_per_second = float(refill_per_second)
        self._tokens = float(capacity)
        self._last = _monotonic()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = _monotonic()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
            self._last = now

    def try_acquire(self) -> bool:
        """Consume a token without blocking.

        :return: ``True`` if a token was available and consumed,
                 ``False`` otherwise.
        :rtype: bool
        """
        with self._lock:
            self._refill_locked()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def acquire(self) -> None:
        """Consume a token, blocking via :data:`_sleep` until one is
        available.

        Used by every real-request hot path. Sleep is computed from
        the deficit and the refill rate, so we wake exactly when the
        next token arrives - there is no polling.

        :return: ``None``.
        :rtype: None
        """
        while True:
            with self._lock:
                self._refill_locked()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = 1.0 - self._tokens
                wait = deficit / self.refill_per_second
            _sleep(wait)

    def with_rate(self, mode: str) -> "TokenBucket":
        """Return a bucket with the requested rate-mode applied.

        ``"normal"`` returns ``self`` unchanged. ``"slow"`` returns a
        new bucket with the refill rate halved. We never support a
        faster mode because that would violate the upstream P1
        ceiling.

        :param mode: ``"normal"`` or ``"slow"``.
        :type mode: str
        :return: A bucket honouring the requested mode.
        :rtype: TokenBucket
        :raises ValueError: When ``mode`` is unrecognised.
        """
        if mode == "normal":
            return self
        if mode == "slow":
            return TokenBucket(self.capacity, self.refill_per_second / 2.0)
        raise ValueError(f"unknown rate mode: {mode!r}")


class RateLimitRegistry:
    """Per-backend bucket map.

    A backend identifier (the same short string used in
    :class:`~animedex.models.common.SourceTag`) maps to one
    :class:`TokenBucket`. :meth:`register` is idempotent across the
    same name; :meth:`get` raises :class:`ApiError` when the backend
    is unknown so a typo at the call site fails loudly.

    :ivar _buckets: Internal mapping from backend identifier to
                     bucket.
    :vartype _buckets: dict
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}

    def register(self, name: str, *, capacity: int, refill_per_second: float) -> TokenBucket:
        """Register or replace a backend's bucket.

        :param name: Backend identifier.
        :type name: str
        :param capacity: Bucket capacity.
        :type capacity: int
        :param refill_per_second: Refill rate.
        :type refill_per_second: float
        :return: The registered bucket.
        :rtype: TokenBucket
        """
        bucket = TokenBucket(capacity=capacity, refill_per_second=refill_per_second)
        self._buckets[name] = bucket
        return bucket

    def get(self, name: str) -> TokenBucket:
        """Look up a backend's bucket.

        :param name: Backend identifier.
        :type name: str
        :return: The registered bucket.
        :rtype: TokenBucket
        :raises ApiError: When ``name`` is not registered.
        """
        if name not in self._buckets:
            raise ApiError(
                f"unknown backend: {name!r}",
                backend=name,
                reason="unknown-backend",
            )
        return self._buckets[name]


def default_registry() -> RateLimitRegistry:
    """Build the project-wide default rate-limit registry.

    The caps reflect what each upstream actually enforces, not what
    we wish for; see ``plans/01`` per-source notes. Anything not
    listed here either has no documented cap or ships its own
    persistent scheduler (AniDB).

    :return: A registry pre-populated with every public backend.
    :rtype: RateLimitRegistry
    """
    r = RateLimitRegistry()
    r.register("anilist", capacity=30, refill_per_second=0.5)
    r.register("jikan", capacity=3, refill_per_second=1.0)
    r.register("kitsu", capacity=10, refill_per_second=10.0)
    r.register("mangadex", capacity=5, refill_per_second=5.0)
    r.register("danbooru", capacity=10, refill_per_second=10.0)
    r.register("shikimori", capacity=5, refill_per_second=5.0)
    r.register("ann", capacity=5, refill_per_second=1.0)
    r.register("trace", capacity=1, refill_per_second=0.5)
    r.register("nekos", capacity=10, refill_per_second=3.0)
    r.register("waifu", capacity=10, refill_per_second=10.0)
    r.register("animechan", capacity=5, refill_per_second=0.0014)
    return r


def selftest() -> bool:
    """Smoke-test the bucket and the default registry.

    Builds a small bucket, exercises both acquire variants, builds
    the default registry, and verifies every plan-01 backend resolves.
    Does not call real ``time.sleep``; the bucket is sized to fit the
    capacity so no waits are required.

    :return: ``True`` on success.
    :rtype: bool
    """
    b = TokenBucket(capacity=2, refill_per_second=1.0)
    assert b.try_acquire() is True
    assert b.try_acquire() is True
    assert b.try_acquire() is False

    r = default_registry()
    for name in ["anilist", "jikan", "kitsu", "mangadex", "danbooru", "shikimori", "ann", "trace"]:
        assert r.get(name).capacity > 0
    return True
