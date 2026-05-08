"""Tests for :mod:`animedex.backends.nekos` (the high-level Python API).

Per AGENTS §9bis: only HTTP transport is mocked; the real
dispatcher / cache / rate-limit / firewall stack runs end-to-end.
Each test loads a captured fixture, registers it with ``responses``,
calls the public function, and asserts on the return shape and the
:class:`NekosImage` projection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import nekos as nekos_api
from animedex.backends.nekos.models import NekosCategoryFormat, NekosImage


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "nekos"


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
    """Register a fixture under URL-path-with-optional-query matching.

    nekos.best response bodies are JSON; we encode them via
    ``responses.json=`` so the dispatcher receives bytes-decodable
    UTF-8.
    """
    import re
    from urllib.parse import urlsplit

    req = fixture["request"]
    resp = fixture["response"]
    path_only = urlsplit(req["url"])
    base = f"{path_only.scheme}://{path_only.netloc}{path_only.path}"
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


class TestCategories:
    def test_categories_returns_alphabetised_names(self, fake_clock):
        fx = _load("endpoints/01-all-categories.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.categories(no_cache=True)
        assert isinstance(out, list)
        assert out == sorted(out)
        assert "husbando" in out
        assert len(out) >= 10  # nekos.best has many SFW categories

    def test_categories_full_returns_typed_dict(self, fake_clock):
        fx = _load("endpoints/01-all-categories.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.categories_full(no_cache=True)
        assert isinstance(out, dict)
        assert "husbando" in out
        for _, fmt in out.items():
            assert isinstance(fmt, NekosCategoryFormat)
            assert fmt.format in ("png", "gif")


class TestImage:
    def test_image_amount_one_returns_single_element_list(self, fake_clock):
        fx = _load("husbando/01-image-amount-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.image("husbando", no_cache=True)
        assert isinstance(out, list)
        assert len(out) == 1
        assert isinstance(out[0], NekosImage)
        assert out[0].url.startswith("https://nekos.best/")

    def test_image_amount_three_returns_three_elements(self, fake_clock):
        fx = _load("husbando/02-image-amount-3.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.image("husbando", amount=3, no_cache=True)
        assert isinstance(out, list)
        assert len(out) == 3
        for img in out:
            assert isinstance(img, NekosImage)

    def test_image_attaches_source_tag_to_each_row(self, fake_clock):
        fx = _load("husbando/01-image-amount-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.image("husbando", no_cache=True)
        assert out[0].source_tag is not None
        assert out[0].source_tag.backend == "nekos"

    def test_image_to_common_projects_to_artpost_with_rating_g(self, fake_clock):
        from animedex.models.art import ArtPost

        fx = _load("husbando/01-image-amount-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.image("husbando", no_cache=True)
        common = out[0].to_common()
        assert isinstance(common, ArtPost)
        assert common.rating == "g"
        assert common.id.startswith("nekos:")
        assert common.url == out[0].url

    def test_image_dimensions_propagate_to_common(self, fake_clock):
        fx = _load("husbando/01-image-amount-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.image("husbando", no_cache=True)
        # Every fixture row carries dimensions; confirm projection
        # threads them through.
        common = out[0].to_common()
        assert common.width is not None and common.width > 0
        assert common.height is not None and common.height > 0


class TestSearch:
    def test_search_query_returns_results(self, fake_clock):
        fx = _load("search/01-frieren-image.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.search("Frieren", amount=5, no_cache=True)
        assert isinstance(out, list)
        # The fixture was captured for amount=5; the upstream returns
        # up to that many. A non-empty list is the contract worth pinning;
        # exact count drift is upstream-controlled.
        assert len(out) >= 1
        for img in out:
            assert isinstance(img, NekosImage)

    def test_search_with_type_two_targets_gif_categories(self, fake_clock):
        fx = _load("search/02-frieren-gif.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = nekos_api.search("Frieren", type=2, amount=3, no_cache=True)
        assert isinstance(out, list)


# ---------- argument validation ----------


class TestBadArgs:
    def test_image_amount_zero_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.image("husbando", amount=0, no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_image_amount_too_high_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.image("husbando", amount=21, no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_image_empty_category_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.image("", no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_image_category_with_slash_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.image("foo/bar", no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_search_type_three_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.search("Frieren", type=3, no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_search_empty_query_raises_bad_args(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            nekos_api.search("", no_cache=True)
        assert ei.value.reason == "bad-args"


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_unknown_category_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/no-such-category",
                json={"message": "Not Found"},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.image("no-such-category", no_cache=True)
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/husbando",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.image("husbando", no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/husbando",
                body="<html>not json</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.image("husbando", no_cache=True)
        assert ei.value.reason == "upstream-decode"

    def test_endpoints_non_dict_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/endpoints",
                json=["unexpected", "list", "shape"],
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.categories(no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_image_results_missing_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/husbando",
                json={"unexpected": "shape"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.image("husbando", no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_search_results_missing_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://nekos.best/api/v2/search",
                json={"oops": "no results key"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                nekos_api.search("Frieren", no_cache=True)
        assert ei.value.reason == "upstream-shape"


# ---------- selftest ----------


def test_module_selftest_returns_true():
    """The high-level module's offline ``selftest()`` must pass."""
    assert nekos_api.selftest() is True
