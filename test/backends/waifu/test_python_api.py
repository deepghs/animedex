"""Tests for :mod:`animedex.backends.waifu` (the high-level Python API)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import waifu as waifu_api
from animedex.backends.waifu.models import WaifuArtist, WaifuImage, WaifuTag


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


class TestArtists:
    def test_artists_returns_typed_list(self, fake_clock):
        fx = _load("artists/01-page-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = waifu_api.artists(no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, WaifuArtist)


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


class TestWaifuAuth:
    """Authenticated reads on Waifu.im (``/users/me``).

    Waifu.im's auth uses ``X-Api-Key`` (not Bearer). The live
    fixture for this endpoint was not captured in this branch
    because the upstream's Cloudflare front-end blocked the
    capture-script's IP after a high-volume probe sequence; these
    tests verify the wire-level header injection and credential
    resolution paths against a stubbed in-line response that mirrors
    a real upstream payload observed during pre-capture probing.
    """

    _USERS_ME_PAYLOAD = {
        "id": 2714,
        "name": "narugo1992",
        "discordId": "1027123926217805888",
        "avatarUrl": "https://cdn.discordapp.com/avatars/x/y.png",
        "role": "User",
        "isBlacklisted": False,
        "blacklistReason": None,
        "requestCount": 10,
        "apiKeyRequestCount": 0,
        "jwtRequestCount": 10,
    }

    def test_me_returns_typed_user(self, fake_clock, monkeypatch):
        from animedex.backends.waifu.models import WaifuUser

        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "fake-key")
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/users/me",
                json=self._USERS_ME_PAYLOAD,
                status=200,
            )
            row = waifu_api.me(no_cache=True)
        assert isinstance(row, WaifuUser)
        assert row.name == "narugo1992"
        assert row.role == "User"

    def test_x_api_key_header_is_injected(self, fake_clock, monkeypatch):
        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "fake-key")
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/users/me",
                json=self._USERS_ME_PAYLOAD,
                status=200,
            )
            waifu_api.me(no_cache=True)
            sent = rsps.calls[0].request
        assert sent.headers.get("X-Api-Key") == "fake-key"
        # Authorization must NOT be set; X-Api-Key is the upstream's
        # only accepted scheme for this token type.
        assert "Authorization" not in sent.headers

    def test_explicit_token_overrides_env(self, fake_clock, monkeypatch):
        monkeypatch.setenv("ANIMEDEX_WAIFU_TOKEN", "env-key")
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.waifu.im/users/me",
                json=self._USERS_ME_PAYLOAD,
                status=200,
            )
            waifu_api.me(token="explicit-key", no_cache=True)
            sent = rsps.calls[0].request
        assert sent.headers.get("X-Api-Key") == "explicit-key"

    def test_no_token_raises_auth_required(self, fake_clock, monkeypatch):
        from animedex.models.common import ApiError

        monkeypatch.delenv("ANIMEDEX_WAIFU_TOKEN", raising=False)
        with pytest.raises(ApiError) as ei:
            waifu_api.me(no_cache=True)
        assert ei.value.reason == "auth-required"


def test_module_selftest_returns_true():
    assert waifu_api.selftest() is True
