"""
Tests for :mod:`animedex.auth.store` (the Protocol),
:mod:`animedex.auth.inmemory_store`, and
:mod:`animedex.auth.keyring_store`.

The token store is a P1 obligation from ``plans/02 §7``: tokens live
in the OS keyring, never on disk in plain text. The tests pin the
small Protocol surface (set/get/delete/keys), the in-memory backend
used by tests and headless CI, and the keyring backend's behaviour
against a faked ``keyring`` module so unit tests do not touch the
real OS keyring.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestProtocol:
    def test_protocol_imports(self):
        from animedex.auth.store import TokenStore

        assert TokenStore is not None


class TestInMemoryStore:
    def test_set_get_delete(self):
        from animedex.auth.inmemory_store import InMemoryTokenStore

        store = InMemoryTokenStore()
        store.set("anilist", "token-a")

        assert store.get("anilist") == "token-a"

        store.delete("anilist")
        assert store.get("anilist") is None

    def test_get_missing_returns_none(self):
        from animedex.auth.inmemory_store import InMemoryTokenStore

        store = InMemoryTokenStore()
        assert store.get("never-set") is None

    def test_keys_returns_known_backends(self):
        from animedex.auth.inmemory_store import InMemoryTokenStore

        store = InMemoryTokenStore()
        store.set("anilist", "x")
        store.set("trace", "y")

        assert sorted(store.keys()) == ["anilist", "trace"]

    def test_initial_seed(self):
        """Constructor accepts a pre-populated mapping for tests."""
        from animedex.auth.inmemory_store import InMemoryTokenStore

        store = InMemoryTokenStore({"anilist": "preseeded"})
        assert store.get("anilist") == "preseeded"


class TestKeyringStore:
    def test_set_dispatches_to_keyring(self, monkeypatch):
        """Verifies the wiring without touching the real OS keyring."""
        from animedex.auth.keyring_store import KeyringTokenStore

        calls = []

        class FakeKeyringModule:
            @staticmethod
            def set_password(service, key, value):
                calls.append(("set", service, key, value))

            @staticmethod
            def get_password(service, key):
                for kind, s, k, v in calls:
                    if kind == "set" and s == service and k == key:
                        return v
                return None

            @staticmethod
            def delete_password(service, key):
                calls.append(("delete", service, key, None))

        monkeypatch.setattr("animedex.auth.keyring_store._keyring", FakeKeyringModule)

        store = KeyringTokenStore(service="animedex-tests")
        store.set("anilist", "token-a")

        assert calls[0] == ("set", "animedex-tests", "anilist", "token-a")
        assert store.get("anilist") == "token-a"

    def test_get_missing_returns_none(self, monkeypatch):
        from animedex.auth.keyring_store import KeyringTokenStore

        class FakeKeyringModule:
            @staticmethod
            def get_password(service, key):
                return None

            @staticmethod
            def set_password(service, key, value):
                pass

            @staticmethod
            def delete_password(service, key):
                pass

        monkeypatch.setattr("animedex.auth.keyring_store._keyring", FakeKeyringModule)

        store = KeyringTokenStore(service="animedex-tests")
        assert store.get("anything") is None

    def test_delete_dispatches_and_drops_known_key(self, monkeypatch):
        from animedex.auth.keyring_store import KeyringTokenStore

        deletions = []

        class FakeKeyringModule:
            @staticmethod
            def get_password(service, key):
                return None

            @staticmethod
            def set_password(service, key, value):
                pass

            @staticmethod
            def delete_password(service, key):
                deletions.append((service, key))

        monkeypatch.setattr("animedex.auth.keyring_store._keyring", FakeKeyringModule)
        store = KeyringTokenStore(service="animedex-tests")
        store.set("anilist", "value")
        assert "anilist" in store.keys()
        store.delete("anilist")
        assert deletions == [("animedex-tests", "anilist")]
        assert "anilist" not in store.keys()

    def test_delete_missing_is_idempotent(self, monkeypatch):
        """Per the TokenStore Protocol contract: deleting a missing entry is not an error.

        Real OS keyring backends (Secret Service, Windows Credential Locker)
        raise :class:`keyring.errors.PasswordDeleteError` when the entry is
        absent; the store must swallow that to honour the Protocol.
        """
        import keyring.errors

        from animedex.auth.keyring_store import KeyringTokenStore

        class FakeKeyringRaisesOnMissing:
            @staticmethod
            def set_password(service, key, value):
                pass

            @staticmethod
            def get_password(service, key):
                return None

            @staticmethod
            def delete_password(service, key):
                raise keyring.errors.PasswordDeleteError("not found")

        monkeypatch.setattr("animedex.auth.keyring_store._keyring", FakeKeyringRaisesOnMissing)
        store = KeyringTokenStore()
        store.delete("never-set")  # must not raise

    def test_keys_reflects_set_only(self, monkeypatch):
        from animedex.auth.keyring_store import KeyringTokenStore

        class FakeKeyringModule:
            @staticmethod
            def get_password(service, key):
                return None

            @staticmethod
            def set_password(service, key, value):
                pass

            @staticmethod
            def delete_password(service, key):
                pass

        monkeypatch.setattr("animedex.auth.keyring_store._keyring", FakeKeyringModule)
        store = KeyringTokenStore()
        store.set("a", "1")
        store.set("b", "2")
        assert sorted(store.keys()) == ["a", "b"]


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.auth import inmemory_store, keyring_store

        assert inmemory_store.selftest() is True
        # The keyring selftest must NOT touch the real OS keyring (per
        # plan 04 phase 0). It should validate the module's import only.
        assert keyring_store.selftest() is True
