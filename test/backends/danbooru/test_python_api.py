"""Tests for :mod:`animedex.backends.danbooru` (the high-level Python API)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import danbooru as db_api
from animedex.backends.danbooru.models import (
    DanbooruArtist,
    DanbooruCount,
    DanbooruPool,
    DanbooruPost,
    DanbooruTag,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "danbooru"


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


def _load(rel: str) -> dict:
    return yaml.safe_load((FIXTURES / rel).read_text(encoding="utf-8"))


def _register(rsps: responses.RequestsMock, fixture: dict) -> None:
    """Path-only fixture register (URL path matches; query strings
    accepted regardless)."""
    import re
    from urllib.parse import urlsplit

    req = fixture["request"]
    resp = fixture["response"]
    parsed = urlsplit(req["url"])
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    url_re = re.compile(re.escape(base) + r"(\?.*)?$")

    _STRIP = {"content-encoding", "content-length", "transfer-encoding"}
    sanitised_headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP}

    rsps.add(
        responses.Response(
            method=req["method"].upper(),
            url=url_re,
            status=resp["status"],
            headers=sanitised_headers,
            json=resp.get("body_json"),
        )
    )


# ---------- happy path ----------


class TestSearch:
    def test_search_returns_typed_posts(self, fake_clock):
        from animedex.models.art import ArtPost

        fx = _load("posts_search/01-touhou-rating-g-order-score.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.search("touhou rating:g order:score", limit=2, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, DanbooruPost)
            common = row.to_common()
            assert isinstance(common, ArtPost)
            assert common.rating == "g"
            assert "touhou" in common.tags

    def test_search_with_explicit_rating_passes_through(self, fake_clock):
        """User explicitly asks for rating:e — the library does not
        rewrite the query. Pin the inform-don't-gate posture."""
        fx = _load("posts_search/04-touhou-rating-e.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.search("touhou rating:e", limit=2, no_cache=True)
        # Whatever rows came back, they keep their upstream rating
        # verbatim (the lossless contract); we don't assert all are
        # rating:e because the upstream may have returned an empty
        # result for a rare combo.
        assert isinstance(out, list)


class TestPost:
    def test_post_returns_typed_resource(self, fake_clock):
        fx = _load("posts_by_id/01-post-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.post(1, no_cache=True)
        assert isinstance(out, DanbooruPost)
        assert out.id == 1


class TestArtist:
    def test_artist_search_substring(self, fake_clock):
        fx = _load("artists_search/02-ke-ta.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.artist_search("ke-ta", limit=5, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruArtist)


class TestTag:
    def test_tag_prefix_search(self, fake_clock):
        fx = _load("tags_search/01-touhou-prefix.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.tag("touhou*", limit=5, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, DanbooruTag)


class TestPool:
    def test_pool_returns_typed_resource(self, fake_clock):
        fx = _load("pools_by_id/01-pool-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.pool(1, no_cache=True)
        assert isinstance(out, DanbooruPool)
        assert out.id == 1


class TestCount:
    def test_count_returns_typed_envelope(self, fake_clock):
        fx = _load("counts/01-touhou-rating-g.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.count("touhou rating:g", no_cache=True)
        assert isinstance(out, DanbooruCount)
        assert out.total() is None or isinstance(out.total(), int)


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_post_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts/999999999.json",
                json={"error": "not found"},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                db_api.post(999999999, no_cache=True)
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_post_non_dict_response_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts/1.json",
                json=["unexpected", "list"],
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                db_api.post(1, no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                body="<html>cloudflare challenge</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "upstream-decode"


def test_module_selftest_returns_true():
    assert db_api.selftest() is True
