"""Tests for aggregate prefix-encoded entity references."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


class TestPrefixIds:
    def test_parse_supported_prefixes(self):
        from animedex.agg._prefix_id import parse

        assert parse("anilist:154587").backend == "anilist"
        assert parse("mal:52991").backend == "jikan"
        assert parse("myanimelist:52991").backend == "jikan"
        assert parse("mangadex:dc8bbc4c-eb7a-4d27-b96a-9aa8c8db4adb").backend == "mangadex"

    def test_rejects_unknown_prefix(self):
        from animedex.agg._prefix_id import parse
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="unknown prefix") as excinfo:
            parse("badprefix:1")
        assert excinfo.value.reason == "bad-args"

    def test_rejects_bad_numeric_id_before_http(self):
        from animedex.agg._prefix_id import parse
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="ID is not numeric") as excinfo:
            parse("anilist:abc")
        assert excinfo.value.backend == "anilist"
        assert excinfo.value.reason == "bad-args"

    def test_anidb_is_deferred_explicitly(self):
        from animedex.agg._prefix_id import parse
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="AniDB high-level helpers are not shipped yet") as excinfo:
            parse("anidb:42")
        assert excinfo.value.backend == "anidb"
        assert excinfo.value.reason == "auth-required"

    def test_prefix_for_backend(self):
        from animedex.agg._prefix_id import prefix_for_backend

        assert prefix_for_backend("jikan", 52991) == "mal:52991"
        assert prefix_for_backend("anilist", 154587) == "anilist:154587"
        assert prefix_for_backend("unknown", 1) is None
        assert prefix_for_backend("anilist", None) is None
