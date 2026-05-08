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


class TestMangaDexAuth:
    """Authenticated reads on the ``/user/*`` and ``/manga/*/status``
    surface. Tests stub the OAuth2 password-grant call so they stay
    offline; the live OAuth flow is exercised by the capture script.
    """

    @pytest.fixture(autouse=True)
    def _stub_oauth(self, monkeypatch):
        """Replace :func:`get_bearer_token` with a static stub so
        the test does not actually round-trip auth.mangadex.org."""
        monkeypatch.setattr(
            "animedex.backends.mangadex.get_bearer_token",
            lambda creds=None, **kw: "stub-bearer-token",
        )

    def test_me_returns_typed_user(self, fake_clock):
        from animedex.backends.mangadex.models import MangaDexUser

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("user_me/01-default.yaml"))
            row = md_api.me(creds="a:b:c:d", no_cache=True)
        assert isinstance(row, MangaDexUser)
        assert row.attributes is not None
        assert row.attributes.username

    def test_authorization_header_is_bearer(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("user_me/01-default.yaml"))
            md_api.me(creds="a:b:c:d", no_cache=True)
            sent = rsps.calls[0].request
        assert sent.headers.get("Authorization") == "Bearer stub-bearer-token"

    def test_my_follows_manga_returns_list(self, fake_clock):
        from animedex.backends.mangadex.models import MangaDexManga

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("user_follows_manga/01-default.yaml"))
            rows = md_api.my_follows_manga(limit=2, creds="a:b:c:d", no_cache=True)
        assert isinstance(rows, list)
        for r in rows:
            assert isinstance(r, MangaDexManga)

    def test_is_following_manga_404_returns_false(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("user_follows_manga_by_id_not_followed/01-default.yaml"))
            result = md_api.is_following_manga("801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True)
        assert result is False

    def test_my_manga_status_normalises_empty_list_to_dict(self, fake_clock):
        # The real upstream returns ``statuses: []`` for an empty
        # account; the helper must normalise to ``{}``.
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("manga_status/01-default.yaml"))
            statuses = md_api.my_manga_status(creds="a:b:c:d", no_cache=True)
        assert statuses == {}

    def test_my_manga_read_markers_returns_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("manga_read_markers/01-default.yaml"))
            chapters = md_api.my_manga_read_markers(
                "801513ba-a712-498c-8f57-cae55b38cc92", creds="a:b:c:d", no_cache=True
            )
        assert isinstance(chapters, list)


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


def test_module_selftest_returns_true():
    """The high-level module's offline ``selftest()`` must pass."""
    assert md_api.selftest() is True
