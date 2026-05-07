"""
Tests for :mod:`animedex.config.profile`.

The :class:`Config` object is the programmatic equivalent of the CLI
flag stack (per ``plans/05 §4``). Its tests pin: defaults map to
unflagged CLI behaviour, every flag has one and only one
corresponding field, the ``rate`` literal accepts the two values the
substrate speaks, and ``effective_token_store`` resolves to a
sensible default when the caller passes ``None``.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestConfigDefaults:
    def test_zero_arg_construction(self):
        from animedex.config.profile import Config

        cfg = Config()
        # The defaults reproduce unflagged CLI behaviour.
        assert cfg.rate == "normal"
        assert cfg.cache_ttl_seconds is None
        assert cfg.no_cache is False
        assert cfg.source_attribution is True
        assert cfg.user_agent is None
        assert cfg.timeout_seconds == 30.0
        assert cfg.token_store is None

    def test_full_construction(self):
        from animedex.auth.inmemory_store import InMemoryTokenStore
        from animedex.config.profile import Config

        store = InMemoryTokenStore()
        cfg = Config(
            rate="slow",
            cache_ttl_seconds=600,
            no_cache=True,
            source_attribution=False,
            user_agent="my-bot/1.0 (+x@x.invalid)",
            timeout_seconds=10.0,
            token_store=store,
        )
        assert cfg.rate == "slow"
        assert cfg.cache_ttl_seconds == 600
        assert cfg.no_cache is True
        assert cfg.source_attribution is False
        assert cfg.user_agent == "my-bot/1.0 (+x@x.invalid)"
        assert cfg.timeout_seconds == 10.0
        assert cfg.token_store is store

    def test_rate_must_be_known_literal(self):
        """Anything outside ``normal`` / ``slow`` is rejected."""
        from animedex.config.profile import Config

        with pytest.raises(Exception):
            Config(rate="fast")


class TestEffectiveTokenStore:
    def test_explicit_store_returned_unchanged(self):
        from animedex.auth.inmemory_store import InMemoryTokenStore
        from animedex.config.profile import Config

        store = InMemoryTokenStore({"a": "b"})
        cfg = Config(token_store=store)
        assert cfg.effective_token_store() is store

    def test_default_resolves_to_keyring_backed_store(self):
        from animedex.auth.keyring_store import KeyringTokenStore
        from animedex.config.profile import Config

        cfg = Config()
        resolved = cfg.effective_token_store()
        assert isinstance(resolved, KeyringTokenStore)


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.config import profile

        assert profile.selftest() is True
