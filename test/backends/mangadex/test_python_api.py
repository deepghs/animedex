"""Tests for :mod:`animedex.backends.mangadex` (the high-level Python API).

Per AGENTS §9bis: only HTTP transport is mocked. Captured fixtures
under ``test/fixtures/mangadex/`` drive every test.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import mangadex as md_api
from animedex.backends.mangadex.models import (
    MangaDexChapter,
    MangaDexCover,
    MangaDexManga,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "mangadex"


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze the ratelimit + cache clocks (HTTP-adjacent only)."""
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
    """Path-only register: the fixture URL's path determines the
    mock route, query strings are accepted regardless. Necessary
    because PR #4 fixtures were captured with ad-hoc query values
    that don't match the high-level API's defaults."""
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


class TestShow:
    def test_show_returns_typed_manga(self, fake_clock):
        fx = _load("manga_by_id/02-berserk.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.show("801513ba-a712-498c-8f57-cae55b38cc92", no_cache=True)
        assert isinstance(out, MangaDexManga)
        assert out.id == "801513ba-a712-498c-8f57-cae55b38cc92"
        assert out.attributes is not None

    def test_show_to_common_projects_to_manga(self, fake_clock):
        from animedex.models.manga import Manga

        fx = _load("manga_by_id/02-berserk.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.show("801513ba-a712-498c-8f57-cae55b38cc92", no_cache=True)
        common = out.to_common()
        assert isinstance(common, Manga)
        assert common.id == "mangadex:801513ba-a712-498c-8f57-cae55b38cc92"
        assert common.title  # non-empty


class TestSearch:
    def test_search_returns_list_of_manga(self, fake_clock):
        fx = _load("manga_search/01-berserk.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.search("Berserk", limit=3, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, MangaDexManga)


class TestFeed:
    def test_feed_returns_list_of_chapters(self, fake_clock):
        fx = _load("manga_feed/02-berserk.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.feed(
                "801513ba-a712-498c-8f57-cae55b38cc92",
                lang="en",
                limit=5,
                no_cache=True,
            )
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, MangaDexChapter)


class TestChapter:
    def test_chapter_returns_typed_resource(self, fake_clock):
        fx = _load("chapter_by_id/01-berserk-ch1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.chapter("01e9f0cb-caea-406d-92bb-0cc67c37481d", no_cache=True)
        assert isinstance(out, MangaDexChapter)
        assert out.id == "01e9f0cb-caea-406d-92bb-0cc67c37481d"
        common = out.to_common()
        assert common.id == "mangadex:01e9f0cb-caea-406d-92bb-0cc67c37481d"


class TestCover:
    def test_cover_returns_typed_resource(self, fake_clock):
        fx = _load("cover_by_id/01-cover-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = md_api.cover("f73c6872-01ee-4ed5-86d1-3520dc250dc4", no_cache=True)
        assert isinstance(out, MangaDexCover)
        assert out.attributes is not None
        assert out.attributes.fileName is not None


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/zzz-notfound",
                json={"result": "error", "errors": [{"title": "Not Found"}]},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                md_api.show("zzz-notfound", no_cache=True)
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/anything",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                md_api.show("anything", no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_result_error_raises_upstream_shape(self, fake_clock):
        """MangaDex envelopes carry ``result: 'error'`` even on 200
        when the upstream rejects an argument validation. Surface as
        typed ``upstream-shape`` so callers can branch."""
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/some-id",
                json={
                    "result": "error",
                    "errors": [{"title": "Validation Error", "detail": "bad uuid"}],
                },
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                md_api.show("some-id", no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/anything",
                body="<html>oops</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                md_api.show("anything", no_cache=True)
        assert ei.value.reason == "upstream-decode"

    def test_missing_data_key_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/anything",
                json={"result": "ok", "oops": "no data"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                md_api.show("anything", no_cache=True)
        assert ei.value.reason == "upstream-shape"


def test_module_selftest_returns_true():
    """The high-level module's offline ``selftest()`` must pass."""
    assert md_api.selftest() is True
