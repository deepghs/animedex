"""
Tests for :mod:`animedex.transport.read_only`.

The read-only firewall is a P1 contract from ``plans/03 §7``: every
``animedex api`` call must reject mutating HTTP methods and known
mutation paths *before* the request leaves the host. It cannot
dispatch on method alone because GraphQL POST and Trace.moe POST are
both legitimate reads. The tests pin the per-backend rules.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestRejectMutatingMethod:
    @pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
    @pytest.mark.parametrize(
        "backend",
        ["anilist", "jikan", "kitsu", "mangadex", "danbooru", "shikimori", "ann", "trace", "ghibli", "quote"],
    )
    def test_universally_rejected(self, backend, method):
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError) as ei:
            enforce_read_only(backend, method, "/anything")
        assert ei.value.reason == "read-only"


class TestPostPolicyPerBackend:
    def test_anilist_post_root_allowed(self):
        from animedex.transport.read_only import enforce_read_only

        enforce_read_only("anilist", "POST", "/")

    def test_anilist_post_other_path_rejected(self):
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError):
            enforce_read_only("anilist", "POST", "/some/other/path")

    @pytest.mark.parametrize(
        "backend", ["jikan", "kitsu", "danbooru", "shikimori", "ann", "mangadex", "ghibli", "quote"]
    )
    def test_post_rejected_for_pure_rest_backends(self, backend):
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError):
            enforce_read_only(backend, "POST", "/anything")

    def test_trace_post_search_allowed(self):
        from animedex.transport.read_only import enforce_read_only

        enforce_read_only("trace", "POST", "/search")

    def test_trace_post_other_rejected(self):
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError):
            enforce_read_only("trace", "POST", "/me")


class TestGetAlwaysAllowed:
    @pytest.mark.parametrize(
        "backend",
        ["anilist", "jikan", "kitsu", "mangadex", "danbooru", "shikimori", "ann", "trace", "ghibli", "quote"],
    )
    def test_get_allowed(self, backend):
        from animedex.transport.read_only import enforce_read_only

        enforce_read_only(backend, "GET", "/anything")


class TestUnknownBackend:
    def test_unknown_backend_rejected(self):
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError) as ei:
            enforce_read_only("not-a-backend", "GET", "/")
        assert ei.value.reason == "unknown-backend"


class TestErrorMessageNamesPolicy:
    def test_message_carries_policy_pointer(self):
        """Per the spec the rejection must name the policy, not say `405`."""
        from animedex.models.common import ApiError
        from animedex.transport.read_only import enforce_read_only

        with pytest.raises(ApiError) as ei:
            enforce_read_only("anilist", "DELETE", "/")
        assert "read-only" in str(ei.value).lower()


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.transport import read_only

        assert read_only.selftest() is True
