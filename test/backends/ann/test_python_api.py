"""Tests for :mod:`animedex.backends.ann`."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import ann as ann_api
from animedex.backends.ann.models import AnnAnimeResponse, AnnReport


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "ann"


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze HTTP-adjacent clocks."""
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
    """Register an ANN XML fixture under its exact captured URL."""
    req = fixture["request"]
    resp = fixture["response"]
    headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP_HEADERS}
    rsps.add(
        responses.Response(
            method=req["method"].upper(),
            url=req["url"],
            status=resp["status"],
            headers=headers,
            body=resp.get("body_text") or "",
        )
    )


_STRIP_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


class TestShow:
    def test_show_returns_typed_anime_response(self, fake_clock):
        fx = _load("by_id/14-id-38838-frieren.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = ann_api.show(38838, no_cache=True)

        assert isinstance(out, AnnAnimeResponse)
        assert out.warnings == []
        assert len(out.anime) == 1
        anime = out.anime[0]
        assert anime.id == "38838"
        assert anime.source_tag is not None
        assert anime.source_tag.backend == "ann"
        assert "Frieren" in (anime.name or "")
        common = anime.to_common()
        assert common.id == "ann:38838"
        assert common.source.backend == "ann"

    def test_missing_id_warning_is_not_error(self, fake_clock):
        fx = _load("by_id/15-id-99999999-missing.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = ann_api.show(99999999, no_cache=True)

        assert isinstance(out, AnnAnimeResponse)
        assert out.anime == []
        assert out.warnings == ["no result for anime=99999999"]


class TestSearch:
    def test_search_returns_multiple_anime_entries(self, fake_clock):
        fx = _load("substring_search/01-frieren.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = ann_api.search("Frieren", no_cache=True)

        assert isinstance(out, AnnAnimeResponse)
        assert len(out.anime) >= 1
        assert out.anime[0].id == "38838"

    def test_search_warning_is_not_error(self, fake_clock):
        fx = _load("substring_search/16-nonexistent.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = ann_api.search("ZZZZNonexistent", no_cache=True)

        assert out.anime == []
        assert out.warnings == ["no results for anime=~ZZZZNonexistent"]


class TestReports:
    def test_reports_returns_typed_items(self, fake_clock):
        fx = _load("reports/01-anime-recently-modified-2.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = ann_api.reports(id=155, type="anime", nlist=2, no_cache=True)

        assert isinstance(out, AnnReport)
        assert out.attrs["listed"] == "2"
        assert len(out.items) == 2
        assert out.items[0].fields["id"]
        assert out.source_tag is not None
        assert out.source_tag.backend == "ann"


class TestErrorPaths:
    def test_reports_html_error_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        fx = _load("reports/16-invalid-report-id.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            with pytest.raises(ApiError) as ei:
                ann_api.reports(id=99999999, type="anime", nlist=2, no_cache=True)

        assert ei.value.reason == "not-found"
