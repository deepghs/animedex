"""Tests for :mod:`animedex.backends.shikimori`."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import shikimori as shiki_api
from animedex.backends.shikimori.models import (
    ShikimoriAnime,
    ShikimoriCalendarEntry,
    ShikimoriCharacter,
    ShikimoriPerson,
    ShikimoriResource,
    ShikimoriScreenshot,
    ShikimoriStudio,
    ShikimoriTopic,
    ShikimoriVideo,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "shikimori"


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
    """Register a fixture under URL-path-with-optional-query matching."""
    import re
    from urllib.parse import urlsplit

    req = fixture["request"]
    resp = fixture["response"]
    parsed = urlsplit(req["url"])
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    url_re = re.compile(re.escape(base) + r"(\?.*)?$")
    headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP_HEADERS}
    kwargs = {"status": resp["status"], "headers": headers}
    if resp.get("body_json") is not None:
        kwargs["json"] = resp["body_json"]
    else:
        kwargs["body"] = resp.get("body_text") or ""
    rsps.add(responses.Response(method=req["method"].upper(), url=url_re, **kwargs))


_STRIP_HEADERS = {"content-encoding", "content-length", "transfer-encoding"}


class TestAnime:
    def test_show_returns_typed_anime(self, fake_clock):
        fx = _load("animes_by_id/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.show(52991, no_cache=True)

        assert isinstance(out, ShikimoriAnime)
        assert out.id == 52991
        assert out.source_tag is not None
        assert out.source_tag.backend == "shikimori"
        common = out.to_common()
        assert common.id == "shikimori:52991"
        assert common.ids["mal"] == "52991"

    def test_search_returns_typed_rows(self, fake_clock):
        fx = _load("animes_search/01-frieren.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.search("Frieren", limit=2, no_cache=True)

        assert isinstance(out, list)
        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriAnime)

    def test_not_found_raises_typed_error(self, fake_clock):
        from animedex.models.common import ApiError

        fx = _load("animes_by_id/16-invalid-99999999.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            with pytest.raises(ApiError) as ei:
                shiki_api.show(99999999, no_cache=True)

        assert ei.value.reason == "not-found"


class TestCalendar:
    def test_calendar_returns_entries(self, fake_clock):
        fx = _load("calendar/01-limit-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.calendar(limit=1, no_cache=True)

        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriCalendarEntry)
        assert out[0].anime is not None


class TestMedia:
    def test_screenshots_returns_typed_rows(self, fake_clock):
        fx = _load("screenshots/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.screenshots(52991, no_cache=True)

        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriScreenshot)

    def test_videos_returns_typed_rows(self, fake_clock):
        fx = _load("videos/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.videos(52991, no_cache=True)

        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriVideo)


class TestLongTail:
    def test_roles_characters_and_staff_return_typed_rows(self, fake_clock):
        fx = _load("roles/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            roles = shiki_api.roles(52991, no_cache=True)
            characters = shiki_api.characters(52991, no_cache=True)
            staff = shiki_api.staff(52991, no_cache=True)

        assert len(roles) >= 1
        assert isinstance(roles[0], ShikimoriResource)
        assert any(isinstance(row, ShikimoriCharacter) for row in characters)
        assert isinstance(staff, list)
        assert all(isinstance(row, ShikimoriPerson) for row in staff)

    def test_similar_related_and_external_links_return_typed_rows(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("similar/01-frieren-52991.yaml"))
            _register(rsps, _load("related/01-frieren-52991.yaml"))
            _register(rsps, _load("external_links/01-frieren-52991.yaml"))
            similar = shiki_api.similar(52991, no_cache=True)
            related = shiki_api.related(52991, no_cache=True)
            links = shiki_api.external_links(52991, no_cache=True)

        assert isinstance(similar, list)
        assert all(isinstance(row, ShikimoriAnime) for row in similar)
        assert isinstance(related, list)
        assert all(isinstance(row, ShikimoriResource) for row in related)
        assert isinstance(links, list)
        assert all(isinstance(row, ShikimoriResource) for row in links)

    def test_topics_studios_and_genres_return_typed_rows(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("topics/01-frieren-52991.yaml"))
            _register(rsps, _load("studios/01-all.yaml"))
            _register(rsps, _load("genres/01-all.yaml"))
            topics = shiki_api.topics(52991, limit=3, no_cache=True)
            studios = shiki_api.studios(no_cache=True)
            genres = shiki_api.genres(no_cache=True)

        assert len(topics) >= 1
        assert isinstance(topics[0], ShikimoriTopic)
        assert len(studios) >= 1
        assert isinstance(studios[0], ShikimoriStudio)
        assert len(genres) >= 1
        assert isinstance(genres[0], ShikimoriResource)
