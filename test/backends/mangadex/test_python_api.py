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
    MangaDexResource,
)
from animedex.backends.mangadex._auth import _TOKEN_URL


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


def _register_as(rsps: responses.RequestsMock, fixture: dict, path: str) -> None:
    """Register a real fixture response body under the wrapper path
    currently being exercised."""
    import re

    resp = fixture["response"]
    url_re = re.compile(re.escape(f"https://api.mangadex.org{path}") + r"(\?.*)?$")

    _STRIP = {"content-encoding", "content-length", "transfer-encoding"}
    sanitised_headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP}

    rsps.add(
        responses.Response(
            method=fixture["request"]["method"].upper(),
            url=url_re,
            status=resp["status"],
            headers=sanitised_headers,
            json=resp.get("body_json"),
        )
    )


def _register_oauth_token(rsps: responses.RequestsMock, token: str = "stub-bearer-token", client_id: str = "a") -> None:
    rsps.add(
        responses.POST,
        _TOKEN_URL,
        json={"access_token": token, "expires_in": 900},
        status=200,
    )
    from animedex.backends.mangadex import _auth

    _auth._TOKEN_CACHE.pop(client_id, None)


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

    def test_to_common_fallbacks(self):
        from animedex.models.manga import Manga

        row = MangaDexManga.model_validate(
            {
                "id": "fallback",
                "type": "manga",
                "attributes": {
                    "title": {"ja-ro": "Romaji", "ja": "Native"},
                    "description": {"fr": "French"},
                    "status": None,
                    "publicationDemographic": None,
                },
            }
        )
        common = row.to_common()
        assert isinstance(common, Manga)
        assert common.title == "Romaji"
        assert common.description == "French"
        assert common.status is None
        assert common.format is None

        edge = MangaDexManga.model_validate(
            {
                "id": "edge",
                "type": "manga",
                "attributes": {
                    "title": [],
                    "description": {"fr": ""},
                    "status": "mystery",
                    "publicationDemographic": "shounen",
                },
            }
        )
        edge_common = edge.to_common()
        assert edge_common.title == ""
        assert edge_common.description is None
        assert edge_common.status == "unknown"
        assert edge_common.source.backend == "mangadex"


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


_MANGADEX_RESOURCE_LIST_WRAPPERS = [
    ("recommendation", "manga_recommendation/01-berserk.yaml", ("801513ba-a712-498c-8f57-cae55b38cc92",)),
    ("manga_tag", "manga_tag/01-all.yaml", ()),
    ("author_search", "author_search/01-page1.yaml", ()),
    ("group_search", "group_search/01-page1.yaml", ()),
    ("report_reasons", "report_reasons_category/01-manga.yaml", ("manga",)),
]

_MANGADEX_RESOURCE_SHOW_WRAPPERS = [
    ("author", "author_by_id/01-first.yaml"),
    ("group", "group_by_id/01-first.yaml"),
]

_MANGADEX_SYNTH_RESOURCE_WRAPPERS = [
    ("aggregate", "manga_aggregate/01-berserk.yaml", ("801513ba-a712-498c-8f57-cae55b38cc92",)),
    ("statistics_manga", "statistics_manga_single/01-berserk.yaml", ("801513ba-a712-498c-8f57-cae55b38cc92",)),
    ("statistics_manga_batch", "statistics_manga_search/01-berserk-only.yaml", ()),
    ("statistics_chapter", "statistics_chapter_single/01-berserk-ch.yaml", ("01e9f0cb-caea-406d-92bb-0cc67c37481d",)),
    ("statistics_chapter_batch", "statistics_chapter_search/01-berserk-only.yaml", ()),
    ("statistics_group", "statistics_group/01-first.yaml", ("6f066753-22c8-4e55-83fa-72fd39819dfd",)),
]


@pytest.mark.parametrize("fn_name,fixture_rel,args", _MANGADEX_RESOURCE_LIST_WRAPPERS)
def test_resource_list_wrappers_return_typed_rows(fn_name, fixture_rel, args, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        rows = getattr(md_api, fn_name)(*args, no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, MangaDexResource)


def test_author_and_group_search_name_filters(fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load("author_search/01-page1.yaml"))
        rows = md_api.author_search(name="Miura", no_cache=True)
        sent = rsps.calls[0].request
    assert isinstance(rows, list)
    assert "name=Miura" in sent.url

    with responses.RequestsMock() as rsps:
        _register(rsps, _load("group_search/01-page1.yaml"))
        rows = md_api.group_search(name="MangaDex", no_cache=True)
        sent = rsps.calls[0].request
    assert isinstance(rows, list)
    assert "name=MangaDex" in sent.url


@pytest.mark.parametrize("fn_name,fixture_rel", _MANGADEX_RESOURCE_SHOW_WRAPPERS)
def test_resource_show_wrappers_return_typed_resource(fn_name, fixture_rel, fake_clock):
    fx = _load(fixture_rel)
    rec_id = fx["response"]["body_json"]["data"]["id"]
    with responses.RequestsMock() as rsps:
        _register(rsps, fx)
        row = getattr(md_api, fn_name)(rec_id, no_cache=True)
    assert isinstance(row, MangaDexResource)


@pytest.mark.parametrize("fn_name,fixture_rel,args", _MANGADEX_SYNTH_RESOURCE_WRAPPERS)
def test_synthetic_resource_wrappers_return_typed_resource(fn_name, fixture_rel, args, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        row = getattr(md_api, fn_name)(*args, no_cache=True)
    assert isinstance(row, MangaDexResource)


def test_public_user_returns_typed_resource(fake_clock):
    fx = _load("user_me/01-default.yaml")
    rec_id = fx["response"]["body_json"]["data"]["id"]
    with responses.RequestsMock() as rsps:
        _register_as(rsps, fx, f"/user/{rec_id}")
        row = md_api.user(rec_id, no_cache=True)
    assert isinstance(row, MangaDexResource)


def test_user_lists_returns_typed_rows(fake_clock):
    fx = _load("user_list/01-default.yaml")
    with responses.RequestsMock() as rsps:
        _register_as(rsps, fx, "/user/user-id/list")
        rows = md_api.user_lists("user-id", no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, MangaDexResource)


def test_list_show_returns_typed_resource(fake_clock):
    fx = _load("user_list/01-default.yaml")
    row_body = {
        "id": "c78bcf99-81c4-4faa-b77d-3d547f7991b7",
        "type": "custom_list",
        "attributes": {"name": "Sample list", "visibility": "public"},
        "relationships": [],
    }
    list_id = row_body["id"]
    with responses.RequestsMock() as rsps:
        _register_as(
            rsps,
            {**fx, "response": {**fx["response"], "body_json": {"result": "ok", "data": row_body}}},
            f"/list/{list_id}",
        )
        row = md_api.list_show(list_id, no_cache=True)
    assert isinstance(row, MangaDexResource)


def test_list_feed_returns_typed_chapters(fake_clock):
    fx = _load("manga_feed/02-berserk.yaml")
    with responses.RequestsMock() as rsps:
        _register_as(rsps, fx, "/list/list-id/feed")
        rows = md_api.list_feed("list-id", no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, MangaDexChapter)


def test_random_manga_returns_typed_resource(fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load("manga_random/01-any.yaml"))
        row = md_api.random_manga(no_cache=True)
    assert isinstance(row, MangaDexManga)


def test_chapter_search_returns_typed_chapters(fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load("chapter_search/01-page1.yaml"))
        rows = md_api.chapter_search(no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, MangaDexChapter)


def test_cover_search_returns_typed_covers(fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load("cover_search/01-page1.yaml"))
        rows = md_api.cover_search(no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, MangaDexCover)


def test_statistics_batch_query_parameters(fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load("statistics_manga_search/01-berserk-only.yaml"))
        row = md_api.statistics_manga_batch(manga=["801513ba-a712-498c-8f57-cae55b38cc92"], no_cache=True)
        sent = rsps.calls[0].request
    assert isinstance(row, MangaDexResource)
    assert "manga%5B%5D=801513ba-a712-498c-8f57-cae55b38cc92" in sent.url

    with responses.RequestsMock() as rsps:
        _register(rsps, _load("statistics_chapter_search/01-berserk-only.yaml"))
        row = md_api.statistics_chapter_batch(chapter=["01e9f0cb-caea-406d-92bb-0cc67c37481d"], no_cache=True)
        sent = rsps.calls[0].request
    assert isinstance(row, MangaDexResource)
    assert "chapter%5B%5D=01e9f0cb-caea-406d-92bb-0cc67c37481d" in sent.url


def test_ping_returns_plain_text(fake_clock):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.mangadex.org/ping", body="pong", status=200)
        assert md_api.ping(no_cache=True) == "pong"


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

    def test_401_raises_auth_required(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.mangadex.org/manga/anything", json={"result": "error"}, status=401)
            with pytest.raises(ApiError) as ei:
                md_api.show("anything", no_cache=True)
        assert ei.value.reason == "auth-required"

    def test_result_error_without_structured_error_uses_default_message(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.mangadex.org/manga/some-id", json={"result": "error"}, status=200)
            with pytest.raises(ApiError) as ei:
                md_api.show("some-id", no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_listing_none_data_returns_empty_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.mangadex.org/manga", json={"result": "ok", "data": None}, status=200)
            rows = md_api.search("empty", no_cache=True)
        assert rows == []

    def test_listing_single_data_object_is_wrapped(self, fake_clock):
        body = {
            "result": "ok",
            "data": {
                "id": "801513ba-a712-498c-8f57-cae55b38cc92",
                "type": "manga",
                "attributes": {"title": {"en": "Berserk"}},
            },
        }
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.mangadex.org/manga", json=body, status=200)
            rows = md_api.search("Berserk", no_cache=True)
        assert len(rows) == 1
        assert isinstance(rows[0], MangaDexManga)


class TestMangaDexAuth:
    """Authenticated reads on the ``/user/*`` and ``/manga/*/status``
    surface. The OAuth token exchange and API calls are both intercepted
    at HTTP transport level; project functions are not monkey-patched.
    """

    def test_me_returns_typed_user(self, fake_clock):
        from animedex.backends.mangadex.models import MangaDexUser

        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("user_me/01-default.yaml"))
            row = md_api.me(creds="a:b:c:d", no_cache=True)
        assert isinstance(row, MangaDexUser)
        assert row.attributes is not None
        assert row.attributes.username

    def test_authorization_header_is_bearer(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("user_me/01-default.yaml"))
            md_api.me(creds="a:b:c:d", no_cache=True)
            sent = rsps.calls[1].request
        assert sent.headers.get("Authorization") == "Bearer stub-bearer-token"

    def test_my_follows_manga_returns_list(self, fake_clock):
        from animedex.backends.mangadex.models import MangaDexManga

        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("user_follows_manga/01-default.yaml"))
            rows = md_api.my_follows_manga(limit=2, creds="a:b:c:d", no_cache=True)
        assert isinstance(rows, list)
        for r in rows:
            assert isinstance(r, MangaDexManga)

    def test_is_following_manga_404_returns_false(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("user_follows_manga_by_id_not_followed/01-default.yaml"))
            result = md_api.is_following_manga("801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True)
        assert result is False

    def test_is_following_manga_200_returns_true(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/user/follows/manga/801513ba-a712-498c-8f57-cae55b38cc92",
                json={"result": "ok"},
                status=200,
            )
            result = md_api.is_following_manga("801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True)
        assert result is True

    def test_my_manga_status_normalises_empty_list_to_dict(self, fake_clock):
        # The real upstream returns ``statuses: []`` for an empty
        # account; the helper must normalise to ``{}``.
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("manga_status/01-default.yaml"))
            statuses = md_api.my_manga_status(creds="a:b:c:d", no_cache=True)
        assert statuses == {}

    @pytest.mark.parametrize(
        "body,expected", [({"result": "ok"}, {}), ({"result": "ok", "statuses": {"x": "reading"}}, {"x": "reading"})]
    )
    def test_my_manga_status_shape_variants(self, body, expected, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(responses.GET, "https://api.mangadex.org/manga/status", json=body, status=200)
            statuses = md_api.my_manga_status(creds="a:b:c:d", no_cache=True)
        assert statuses == expected

    def test_my_manga_status_rejects_non_dict_statuses(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/status",
                json={"result": "ok", "statuses": "reading"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                md_api.my_manga_status(creds="a:b:c:d", no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_my_manga_status_by_id_returns_status(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("manga_status_by_id/01-default.yaml"))
            status = md_api.my_manga_status_by_id(
                "801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True
            )
        assert status is None or isinstance(status, str)

    def test_my_manga_read_markers_returns_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("manga_read_markers/01-default.yaml"))
            chapters = md_api.my_manga_read_markers(
                "801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True
            )
        assert isinstance(chapters, list)

    def test_my_manga_read_markers_non_list_returns_empty(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/801513ba-a712-498c-8f57-cae55b38cc92/read",
                json={"result": "ok", "data": {"unexpected": "object"}},
                status=200,
            )
            chapters = md_api.my_manga_read_markers(
                "801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True
            )
        assert chapters == []

    @pytest.mark.parametrize(
        "fn_name,fixture_rel,expected_type",
        [
            ("my_follows_group", "user_follows_group/01-default.yaml", MangaDexResource),
            ("my_follows_user", "user_follows_user/01-default.yaml", MangaDexResource),
            ("my_follows_list", "user_follows_list/01-default.yaml", MangaDexResource),
            ("my_follows_manga_feed", "user_follows_manga_feed/01-default.yaml", MangaDexChapter),
            ("my_lists", "user_list/01-default.yaml", MangaDexResource),
            ("my_history", "user_history/01-default.yaml", MangaDexResource),
        ],
    )
    def test_authenticated_list_wrappers_return_typed_rows(self, fn_name, fixture_rel, expected_type, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load(fixture_rel))
            rows = getattr(md_api, fn_name)(creds="a:b:c:d", no_cache=True)
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, expected_type)

    @pytest.mark.parametrize(
        "fn_name,path",
        [
            ("is_following_group", "/user/follows/group/group-id"),
            ("is_following_user", "/user/follows/user/user-id"),
        ],
    )
    def test_authenticated_follow_probe_200_returns_true(self, fn_name, path, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(responses.GET, f"https://api.mangadex.org{path}", json={"result": "ok"}, status=200)
            result = getattr(md_api, fn_name)(path.rsplit("/", 1)[-1], creds="a:b:c:d", no_cache=True)
        assert result is True

    def test_authenticated_follow_group_404_returns_false(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register(rsps, _load("user_follows_group_by_id_not_followed/01-default.yaml"))
            result = md_api.is_following_group("0a8eb8f6-ed7b-4db6-90f8-fde18e1842e6", creds="a:b:c:d", no_cache=True)
        assert result is False

    def test_authenticated_follow_user_404_returns_false(self, fake_clock):
        fx = _load("user_follows_group_by_id_not_followed/01-default.yaml")
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            _register_as(rsps, fx, "/user/follows/user/user-id")
            result = md_api.is_following_user("user-id", creds="a:b:c:d", no_cache=True)
        assert result is False

    @pytest.mark.parametrize(
        "fn_name,path,arg",
        [
            ("is_following_manga", "/user/follows/manga/x", "x"),
            ("is_following_group", "/user/follows/group/x", "x"),
            ("is_following_user", "/user/follows/user/x", "x"),
        ],
    )
    def test_authenticated_follow_probe_non_404_reraises(self, fn_name, path, arg, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(responses.GET, f"https://api.mangadex.org{path}", json={"result": "error"}, status=503)
            with pytest.raises(ApiError) as ei:
                getattr(md_api, fn_name)(arg, creds="a:b:c:d", no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_my_history_singleton_payload_is_wrapped(self, fake_clock):
        body = {
            "result": "ok",
            "data": {"id": "history-id", "type": "history", "attributes": {"readDate": "2026-05-08"}},
        }
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(responses.GET, "https://api.mangadex.org/user/history", json=body, status=200)
            rows = md_api.my_history(creds="a:b:c:d", no_cache=True)
        assert len(rows) == 1
        assert isinstance(rows[0], MangaDexResource)

    def test_my_manga_status_filter_threads_parameter(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps)
            rsps.add(
                responses.GET,
                "https://api.mangadex.org/manga/status",
                json={"result": "ok", "statuses": {}},
                status=200,
            )
            statuses = md_api.my_manga_status(status="reading", creds="a:b:c:d", no_cache=True)
            sent = rsps.calls[1].request
        assert statuses == {}
        assert "status=reading" in sent.url


class TestMangaDexCredentialResolution:
    """Pure credential-parsing tests (no HTTP)."""

    def test_creds_string_is_parsed(self):
        from animedex.backends.mangadex._auth import MangaDexCredentials, resolve_credentials

        out = resolve_credentials("a:b:c:d")
        assert isinstance(out, MangaDexCredentials)
        assert out.client_id == "a"
        assert out.password == "d"

    def test_env_var_fallback(self, monkeypatch):
        from animedex.backends.mangadex._auth import resolve_credentials

        monkeypatch.setenv("ANIMEDEX_MANGADEX_CREDS", "x:y:z:w")
        out = resolve_credentials()
        assert out.username == "z"

    def test_config_token_store_fallback(self, monkeypatch):
        from animedex.auth.inmemory_store import InMemoryTokenStore
        from animedex.backends.mangadex._auth import resolve_credentials
        from animedex.config import Config

        monkeypatch.delenv("ANIMEDEX_MANGADEX_CREDS", raising=False)
        out = resolve_credentials(config=Config(token_store=InMemoryTokenStore({"mangadex": "s:t:u:v"})))
        assert out.username == "u"

    def test_no_creds_raises_auth_required(self, monkeypatch):
        from animedex.backends.mangadex._auth import resolve_credentials
        from animedex.models.common import ApiError

        monkeypatch.delenv("ANIMEDEX_MANGADEX_CREDS", raising=False)
        with pytest.raises(ApiError) as ei:
            resolve_credentials()
        assert ei.value.reason == "auth-required"

    def test_malformed_creds_string_raises_bad_args(self):
        from animedex.backends.mangadex._auth import resolve_credentials
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            resolve_credentials("only:three:parts")
        assert ei.value.reason == "bad-args"

    def test_creds_object_passes_through(self):
        from animedex.backends.mangadex._auth import MangaDexCredentials, resolve_credentials

        creds = MangaDexCredentials("a", "b", "c", "d")
        assert resolve_credentials(creds) is creds

    def test_invalid_creds_object_raises_bad_args(self):
        from animedex.backends.mangadex._auth import resolve_credentials
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            resolve_credentials(object())
        assert ei.value.reason == "bad-args"

    def test_get_bearer_token_uses_http_exchange_and_cache(self):
        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token

        _auth._TOKEN_CACHE.pop("cache-client", None)
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps, token="cached-token", client_id="cache-client")
            first = get_bearer_token("cache-client:b:c:d")
            second = get_bearer_token("cache-client:b:c:d")
            assert len([c for c in rsps.calls if "auth.mangadex.org" in c.request.url]) == 1
        assert first == "cached-token"
        assert second == "cached-token"

    def test_get_bearer_token_force_refresh_ignores_cache(self):
        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token

        _auth._TOKEN_CACHE.pop("refresh-client", None)
        with responses.RequestsMock() as rsps:
            _register_oauth_token(rsps, token="first-token", client_id="refresh-client")
            rsps.add(responses.POST, _TOKEN_URL, json={"access_token": "second-token", "expires_in": 900}, status=200)
            assert get_bearer_token("refresh-client:b:c:d") == "first-token"
            assert get_bearer_token("refresh-client:b:c:d", force_refresh=True) == "second-token"

    @pytest.mark.parametrize(
        "status,reason",
        [
            (400, "auth-required"),
            (500, "upstream-error"),
        ],
    )
    def test_get_bearer_token_status_errors(self, status, reason):
        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token
        from animedex.models.common import ApiError

        _auth._TOKEN_CACHE.pop(f"status-{status}", None)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, _TOKEN_URL, body="nope", status=status)
            with pytest.raises(ApiError) as ei:
                get_bearer_token(f"status-{status}:b:c:d")
        assert ei.value.reason == reason

    def test_get_bearer_token_rejects_non_json_response(self):
        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token
        from animedex.models.common import ApiError

        _auth._TOKEN_CACHE.pop("non-json-client", None)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, _TOKEN_URL, body="<html>oops</html>", status=200)
            with pytest.raises(ApiError) as ei:
                get_bearer_token("non-json-client:b:c:d")
        assert ei.value.reason == "upstream-decode"

    def test_get_bearer_token_rejects_missing_access_token(self):
        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token
        from animedex.models.common import ApiError

        _auth._TOKEN_CACHE.pop("missing-token-client", None)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, _TOKEN_URL, json={"expires_in": 900}, status=200)
            with pytest.raises(ApiError) as ei:
                get_bearer_token("missing-token-client:b:c:d")
        assert ei.value.reason == "upstream-shape"

    def test_get_bearer_token_network_error(self):
        from requests import ConnectionError

        from animedex.backends.mangadex import _auth
        from animedex.backends.mangadex._auth import get_bearer_token
        from animedex.models.common import ApiError

        _auth._TOKEN_CACHE.pop("network-error-client", None)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, _TOKEN_URL, body=ConnectionError("offline"))
            with pytest.raises(ApiError) as ei:
                get_bearer_token("network-error-client:b:c:d")
        assert ei.value.reason == "upstream-error"


def test_module_selftest_returns_true():
    """The high-level module's offline ``selftest()`` must pass."""
    assert md_api.selftest() is True


def test_auth_selftest_returns_true():
    from animedex.backends.mangadex import _auth

    assert _auth.selftest() is True


def test_models_selftest_returns_true():
    from animedex.backends.mangadex import models

    assert models.selftest() is True
