"""
Tests for :mod:`animedex.transport.ratelimit`.

The token bucket guards every backend's outgoing-request rate so we
honour the P1 caps from ``plans/02``. The tests here pin: capacity
and refill semantics, blocking acquire (which is what backends use
in practice), the ``slow`` rate override, and the registry that maps
a backend name to its bucket so the substrate can ship a single
configuration table.

A monkeypatched clock keeps the tests both fast and deterministic:
real ``time.sleep`` calls are never made.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


@pytest.fixture
def fake_clock(monkeypatch):
    """Replace ``time.monotonic`` and ``time.sleep`` with a controllable pair."""

    state = {"now": 0.0, "slept": 0.0}

    def now():
        return state["now"]

    def sleep(seconds):
        state["slept"] += seconds
        state["now"] += seconds

    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", now)
    monkeypatch.setattr("animedex.transport.ratelimit._sleep", sleep)

    state["advance"] = lambda secs: state.update(now=state["now"] + secs)
    return state


class TestTokenBucket:
    def test_initial_capacity_full(self, fake_clock):
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=3, refill_per_second=1.0)

        assert b.try_acquire() is True
        assert b.try_acquire() is True
        assert b.try_acquire() is True
        assert b.try_acquire() is False

    def test_refill_over_time(self, fake_clock):
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=2, refill_per_second=1.0)
        b.try_acquire()
        b.try_acquire()
        assert b.try_acquire() is False

        fake_clock["advance"](1.0)
        assert b.try_acquire() is True

    def test_blocking_acquire_waits_for_refill(self, fake_clock):
        """The blocking path is what backends use in practice."""
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=1, refill_per_second=2.0)
        b.acquire()
        b.acquire()
        assert fake_clock["slept"] == pytest.approx(0.5)

    def test_capacity_must_be_positive(self):
        from animedex.transport.ratelimit import TokenBucket

        with pytest.raises(ValueError):
            TokenBucket(capacity=0, refill_per_second=1.0)

    def test_refill_must_be_positive(self):
        from animedex.transport.ratelimit import TokenBucket

        with pytest.raises(ValueError):
            TokenBucket(capacity=1, refill_per_second=0)

    def test_slow_mode_halves_refill(self, fake_clock):
        """``Rate.slow`` is exposed via the bucket factory."""
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=1, refill_per_second=4.0)
        b_slow = b.with_rate("slow")

        assert b_slow.refill_per_second == pytest.approx(2.0)

    def test_normal_mode_unchanged(self, fake_clock):
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=1, refill_per_second=4.0)
        assert b.with_rate("normal") is b

    def test_unknown_rate_mode_rejected(self, fake_clock):
        from animedex.transport.ratelimit import TokenBucket

        b = TokenBucket(capacity=1, refill_per_second=4.0)
        with pytest.raises(ValueError):
            b.with_rate("turbo")


class TestRegistry:
    def test_registry_returns_same_bucket_per_backend(self):
        from animedex.transport.ratelimit import RateLimitRegistry

        r = RateLimitRegistry()
        r.register("anilist", capacity=30, refill_per_second=0.5)

        b1 = r.get("anilist")
        b2 = r.get("anilist")
        assert b1 is b2

    def test_registry_unknown_backend_raises(self):
        from animedex.models.common import ApiError
        from animedex.transport.ratelimit import RateLimitRegistry

        r = RateLimitRegistry()
        with pytest.raises(ApiError):
            r.get("not-a-backend")

    def test_default_registry_has_known_backends(self):
        """The substrate ships sensible defaults for every plan-01 source."""
        from animedex.transport.ratelimit import default_registry

        r = default_registry()
        for name in ["anilist", "jikan", "kitsu", "mangadex", "danbooru", "shikimori", "ann", "trace"]:
            assert r.get(name) is not None


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.transport import ratelimit

        assert ratelimit.selftest() is True
