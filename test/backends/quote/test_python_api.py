"""Tests for :mod:`animedex.backends.quote`.

Only HTTP transport is mocked; the real dispatcher, cache, rate-limit
bucket, firewall, high-level parser, and rich models run end-to-end
against captured AnimeChan fixtures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import quote as quote_api
from animedex.backends.quote import models as quote_models
from animedex.backends.quote.models import AnimeChanAnime, AnimeChanQuote
from animedex.config import Config
from animedex.models.common import ApiError


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "quote"


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze the ratelimit + cache clocks."""
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 9, tzinfo=timezone.utc)}
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
    req = fixture["request"]
    resp = fixture["response"]
    headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() != "content-length"}
    rsps.add(req["method"].upper(), req["url"], json=resp["body_json"], status=resp["status"], headers=headers)


class TestQuoteApi:
    def test_random_returns_quote(self, fake_clock):
        fx = _load("random/01-random.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.random(no_cache=True)
        assert isinstance(out, AnimeChanQuote)
        assert out.content
        assert out.source_tag.backend == "quote"

    def test_random_by_anime_threads_filter(self, fake_clock):
        fx = _load("random_by_anime/01-naruto.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.random_by_anime("Naruto", no_cache=True)
        assert isinstance(out, AnimeChanQuote)
        assert out.anime.name

    def test_random_by_character_threads_filter(self, fake_clock):
        fx = _load("random_by_character/01-saitama.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.random_by_character("Saitama", no_cache=True)
        assert out.character.name == "Saitama"

    def test_quotes_by_anime_returns_list(self, fake_clock):
        fx = _load("quotes_by_anime/01-naruto-page-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.quotes_by_anime("Naruto", page=1, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        assert all(isinstance(row, AnimeChanQuote) for row in out)

    def test_quotes_by_character_returns_list(self, fake_clock):
        fx = _load("quotes_by_character/01-saitama-page-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.quotes_by_character("Saitama", page=1, no_cache=True)
        assert isinstance(out, list)
        assert all(row.character.name == "Saitama" for row in out)

    def test_anime_returns_anime_object(self, fake_clock):
        fx = _load("anime/01-one-punch-man-188.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.anime("188", no_cache=True)
        assert isinstance(out, AnimeChanAnime)
        assert out.id == 188
        assert out.name == "One Punch Man"

    def test_quote_to_common_projects_to_common_quote(self, fake_clock):
        from animedex.models.quote import Quote

        fx = _load("random_by_character/01-saitama.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = quote_api.random_by_character("Saitama", no_cache=True)
        common = out.to_common()
        assert isinstance(common, Quote)
        assert common.text == out.content
        assert common.source.backend == "quote"

    def test_high_level_default_cache_serves_repeat_call(self, fake_clock):
        fx = _load("random/01-random.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            first = quote_api.random(config=Config(cache_ttl_seconds=3600))
        with responses.RequestsMock(assert_all_requests_are_fired=False):
            second = quote_api.random(config=Config(cache_ttl_seconds=3600))
        assert first.content == second.content
        assert first.source_tag.cached is False
        assert second.source_tag.cached is True

    def test_close_default_cache_resets_singleton(self, fake_clock):
        cache = quote_api._default_cache()
        assert quote_api._DEFAULT_CACHE is cache
        quote_api._close_default_cache()
        assert quote_api._DEFAULT_CACHE is None


class TestValidation:
    def test_empty_filter_raises_bad_args(self, fake_clock):
        with pytest.raises(ApiError) as ei:
            quote_api.random_by_anime("", no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_page_zero_raises_bad_args(self, fake_clock):
        with pytest.raises(ApiError) as ei:
            quote_api.quotes_by_anime("Naruto", page=0, no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_429_raises_rate_limited(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/quotes/random",
                json={"message": "Too many requests! Rate limit will reset in 1 hour."},
                status=429,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == "rate-limited"

    @pytest.mark.parametrize(
        ("status", "body", "reason"),
        [
            (404, {"message": "missing"}, "not-found"),
            (500, {"message": "server failed"}, "upstream-error"),
            (400, {"message": "bad input"}, "upstream-error"),
        ],
    )
    def test_http_errors_raise_api_error(self, fake_clock, status, body, reason):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.animechan.io/v1/quotes/random", json=body, status=status)
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == reason

    def test_non_json_body_raises_decode_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.animechan.io/v1/quotes/random", body="not-json", status=200)
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == "upstream-decode"

    def test_non_object_payload_raises_shape_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.animechan.io/v1/quotes/random", json=[], status=200)
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_unsuccessful_envelope_raises_upstream_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/quotes/random",
                json={"status": "error", "message": "temporary failure"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_single_quote_shape_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/quotes/random",
                json={"status": "success", "data": []},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.random(no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_quote_list_shape_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/quotes",
                match=[responses.matchers.query_param_matcher({"anime": "Naruto", "page": "1"})],
                json={"status": "success", "data": {}},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.quotes_by_anime("Naruto", page=1, no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_quote_row_shape_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/quotes",
                match=[responses.matchers.query_param_matcher({"anime": "Naruto", "page": "1"})],
                json={"status": "success", "data": ["not-an-object"]},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.quotes_by_anime("Naruto", page=1, no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_anime_shape_error(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.animechan.io/v1/anime/188",
                json={"status": "success", "data": []},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                quote_api.anime("188", no_cache=True)
        assert ei.value.reason == "upstream-shape"


class TestModelEdges:
    def test_quote_to_common_without_nested_models_uses_default_source(self):
        common = AnimeChanQuote(content="Sample").to_common()
        assert common.text == "Sample"
        assert common.anime is None
        assert common.character is None
        assert common.source.backend == "quote"

    def test_model_selftest_runs(self):
        assert quote_models.selftest() is True


class TestSelftest:
    def test_selftest_runs(self):
        assert quote_api.selftest() is True
