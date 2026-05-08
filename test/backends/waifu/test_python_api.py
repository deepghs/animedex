"""Tests for :mod:`animedex.backends.waifu` (the high-level Python API)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import waifu as waifu_api
from animedex.backends.waifu.models import WaifuArtist, WaifuImage, WaifuStats, WaifuTag


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "waifu"


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
    """Path-only fixture register."""
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


class TestTags:
    def test_tags_returns_typed_list(self, fake_clock):
        fx = _load("tags/01-all.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.tags(no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 5
        for row in out:
            assert isinstance(row, WaifuTag)

    def test_tags_page_size_threads_parameter(self, fake_clock):
        fx = _load("tags/01-all.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.tags(page_size=3, no_cache=True)
            sent = rsps.calls[0].request
        assert isinstance(out, list)
        assert "pageSize=3" in sent.url


class TestArtists:
    def test_artists_returns_typed_list(self, fake_clock):
        fx = _load("artists/01-page-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.artists(no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, WaifuArtist)

    def test_artists_pagination_threads_parameters(self, fake_clock):
        fx = _load("artists/01-page-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.artists(page_number=2, page_size=3, no_cache=True)
            sent = rsps.calls[0].request
        assert isinstance(out, list)
        assert "pageNumber=2" in sent.url
        assert "pageSize=3" in sent.url


class TestImages:
    def test_images_default_returns_typed_list(self, fake_clock):
        fx = _load("images/01-default-page1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, WaifuImage)

    def test_images_default_returns_sfw_only(self, fake_clock):
        """When ``is_nsfw`` is ``None`` (default), upstream returns
        SFW only — pin that the projection's rating is ``"g"``."""
        fx = _load("images/01-default-page1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(no_cache=True)
        # Default upstream behaviour: every row has isNsfw=False.
        for img in out:
            assert img.isNsfw is False
            assert img.to_common().rating == "g"

    def test_images_nsfw_true_returns_nsfw(self, fake_clock):
        """``is_nsfw=True`` opts in to NSFW results."""
        fx = _load("images/04-nsfw-true.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(is_nsfw=True, page_size=3, no_cache=True)
        assert len(out) >= 1
        for img in out:
            assert img.isNsfw is True
            assert img.to_common().rating == "e"

    def test_images_with_included_tag(self, fake_clock):
        fx = _load("images/02-included-waifu.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(included_tags=["waifu"], no_cache=True)
        assert isinstance(out, list)
        for img in out:
            tag_slugs = [t.slug for t in img.tags]
            assert "waifu" in tag_slugs

    def test_images_with_excluded_tag(self, fake_clock):
        fx = _load("images/06-excluded-ero.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(excluded_tags=["ero"], page_size=3, no_cache=True)
        for img in out:
            tag_slugs = [t.slug for t in img.tags]
            assert "ero" not in tag_slugs

    def test_images_animated(self, fake_clock):
        fx = _load("images/05-animated-true.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(is_animated=True, page_size=2, no_cache=True)
        for img in out:
            assert img.isAnimated is True

    def test_images_with_all_optional_filters(self, fake_clock):
        fx = _load("images/03-included-waifu-page-size-3.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.images(
                included_tags=["waifu"],
                excluded_tags=["ero"],
                is_nsfw=False,
                is_animated=False,
                page_number=1,
                page_size=3,
                no_cache=True,
            )
            sent = rsps.calls[0].request
        assert isinstance(out, list)
        assert "included_tags=waifu" in sent.url
        assert "excluded_tags=ero" in sent.url
        assert "isNsfw=false" in sent.url
        assert "isAnimated=false" in sent.url
        assert "pageNumber=1" in sent.url
        assert "pageSize=3" in sent.url


class TestSingleResources:
    def test_tag_by_id_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("tags_by_id/01-id-12-waifu.yaml"))
            row = waifu_api.tag(12, no_cache=True)
        assert isinstance(row, WaifuTag)

    def test_tag_by_slug_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("tags_by_slug/01-slug-waifu.yaml"))
            row = waifu_api.tag_by_slug("waifu", no_cache=True)
        assert isinstance(row, WaifuTag)

    def test_artist_by_id_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("artists_by_id/01-id-80-gongha.yaml"))
            row = waifu_api.artist(80, no_cache=True)
        assert isinstance(row, WaifuArtist)

    def test_artist_by_name_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("artists_by_name/01-name-gongha.yaml"))
            row = waifu_api.artist_by_name("GongHa", no_cache=True)
        assert isinstance(row, WaifuArtist)

    def test_image_by_id_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("images_by_id/01-id-1914.yaml"))
            row = waifu_api.image(1914, no_cache=True)
        assert isinstance(row, WaifuImage)

    def test_stats_public_returns_typed_resource(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("stats_public/01-all.yaml"))
            row = waifu_api.stats_public(no_cache=True)
        assert isinstance(row, WaifuStats)


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/no-such-endpoint",
                json={"detail": "Not Found"},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                waifu_api._fetch("/no-such-endpoint")
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/tags",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                waifu_api.tags(no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_401_raises_auth_required(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.waifu.im/tags", json={"detail": "auth"}, status=401)
            with pytest.raises(ApiError) as ei:
                waifu_api.tags(no_cache=True)
        assert ei.value.reason == "auth-required"

    def test_missing_items_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/tags",
                json={"oops": "no items"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                waifu_api.tags(no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_non_list_items_raise_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.waifu.im/tags", json={"items": {"unexpected": "object"}}, status=200)
            with pytest.raises(ApiError) as ei:
                waifu_api.tags(no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/tags",
                body="<html>oops</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                waifu_api.tags(no_cache=True)
        assert ei.value.reason == "upstream-decode"

    @pytest.mark.parametrize(
        "fn,args,path",
        [
            (waifu_api.tag, (12,), "/tags/12"),
            (waifu_api.tag_by_slug, ("waifu",), "/tags/by-slug/waifu"),
            (waifu_api.artist, (80,), "/artists/80"),
            (waifu_api.artist_by_name, ("GongHa",), "/artists/by-name/GongHa"),
            (waifu_api.image, (1914,), "/images/1914"),
            (waifu_api.stats_public, (), "/stats/public"),
            (waifu_api.me, (), "/users/me"),
        ],
    )
    def test_singleton_bad_shapes_raise_upstream_shape(self, fn, args, path, fake_clock, monkeypatch):
        from animedex.models.common import ApiError

        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "fake-key")
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, f"https://api.waifu.im{path}", json=["unexpected"], status=200)
            with pytest.raises(ApiError) as ei:
                fn(*args, no_cache=True)
        assert ei.value.reason == "upstream-shape"


class TestWaifuAuth:
    """Authenticated reads on Waifu.im (``/users/me``).

    Waifu.im's auth uses ``X-Api-Key`` (not Bearer); the live
    fixture under ``test/fixtures/waifu/users_me/01-default.yaml``
    was captured against a real personal API key (token redacted by
    the capture pipeline before write).
    """

    def test_me_returns_typed_user(self, fake_clock, monkeypatch):
        from animedex.backends.waifu.models import WaifuUser

        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "fake-key")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_me/01-default.yaml"))
            row = waifu_api.me(no_cache=True)
        assert isinstance(row, WaifuUser)
        assert row.id is not None
        assert row.name is not None
        assert row.role is not None

    def test_x_api_key_header_is_injected(self, fake_clock, monkeypatch):
        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "fake-key")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_me/01-default.yaml"))
            waifu_api.me(no_cache=True)
            sent = rsps.calls[0].request
        assert sent.headers.get("X-Api-Key") == "fake-key"
        # Authorization must NOT be set; X-Api-Key is the upstream's
        # only accepted scheme for this token type.
        assert "Authorization" not in sent.headers

    def test_explicit_token_overrides_env(self, fake_clock, monkeypatch):
        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "env-key")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_me/01-default.yaml"))
            waifu_api.me(token="explicit-key", no_cache=True)
            sent = rsps.calls[0].request
        assert sent.headers.get("X-Api-Key") == "explicit-key"

    def test_no_token_raises_auth_required(self, fake_clock, monkeypatch):
        from animedex.models.common import ApiError

        monkeypatch.delenv("ANIMEDEX_WAIFU_TOKEN", raising=False)
        with pytest.raises(ApiError) as ei:
            waifu_api.me(no_cache=True)
        assert ei.value.reason == "auth-required"

    def test_config_token_store_token_is_used(self, fake_clock, monkeypatch):
        from animedex.auth.inmemory_store import InMemoryTokenStore
        from animedex.backends.waifu.models import WaifuUser
        from animedex.config import Config

        monkeypatch.delenv("ANIMEDEX_WAIFU_TOKEN", raising=False)
        cfg = Config(token_store=InMemoryTokenStore({"waifu": "stored-key"}))
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_me/01-default.yaml"))
            row = waifu_api.me(config=cfg, no_cache=True)
            sent = rsps.calls[0].request
        assert isinstance(row, WaifuUser)
        assert sent.headers.get("X-Api-Key") == "stored-key"


def test_module_selftest_returns_true():
    assert waifu_api.selftest() is True


def test_models_selftest_returns_true():
    from animedex.backends.waifu import models

    assert models.selftest() is True
