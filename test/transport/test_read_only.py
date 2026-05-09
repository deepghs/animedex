"""
Tests for :mod:`animedex.transport.read_only`.

The module is an advisory classifier only. It can label whether a
method/path pair is known to be read-only, but it must not reject a
request on the user's behalf.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestClassifyReadOnly:
    def test_known_read_returns_true(self):
        from animedex.transport.read_only import classify_read_only

        assert classify_read_only("anilist", "POST", "/") is True
        assert classify_read_only("trace", "POST", "/search") is True

    def test_unknown_or_mutating_looking_method_returns_false(self):
        from animedex.transport.read_only import classify_read_only

        assert classify_read_only("jikan", "DELETE", "/anime") is False
        assert classify_read_only("mangadex", "POST", "/manga") is False

    def test_unknown_backend_returns_none(self):
        from animedex.transport.read_only import classify_read_only

        assert classify_read_only("not-a-backend", "GET", "/") is None


class TestKnownBackends:
    def test_known_backends_contains_raw_api_backends(self):
        from animedex.transport.read_only import known_backends

        assert set(known_backends()) >= {"anilist", "jikan", "mangadex", "trace", "waifu"}


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.transport import read_only

        assert read_only.selftest() is True
