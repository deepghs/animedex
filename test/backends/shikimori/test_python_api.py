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
    ShikimoriClub,
    ShikimoriManga,
    ShikimoriPerson,
    ShikimoriPublisher,
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


def _register_path(
    rsps: responses.RequestsMock,
    path: str,
    *,
    status: int = 200,
    body="[]",
    content_type: str = "application/json",
) -> None:
    """Register a synthetic Shikimori response by endpoint path."""
    import re

    url_re = re.compile(r"https://shikimori\.io" + re.escape(path) + r"(\?.*)?$")
    rsps.add(
        responses.Response(
            method="GET",
            url=url_re,
            status=status,
            body=body,
            headers={"Content-Type": content_type},
        )
    )


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

    def test_high_level_default_cache_serves_repeat_call(self, fake_clock):
        fx = _load("animes_by_id/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            first = shiki_api.show(52991)
            second = shiki_api.show(52991)

        assert first.source_tag is not None
        assert first.source_tag.cached is False
        assert second.source_tag is not None
        assert second.source_tag.cached is True

    def test_close_default_cache_resets_singleton(self, fake_clock):
        cache = shiki_api._default_cache()

        assert cache is shiki_api._default_cache()
        shiki_api._close_default_cache()
        assert shiki_api._DEFAULT_CACHE is None

    def test_config_threads_transport_defaults(self, fake_clock):
        from animedex.config import Config

        fx = _load("animes_by_id/01-frieren-52991.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.show(52991, config=Config(no_cache=True, cache_ttl_seconds=30, rate="slow"))

        assert isinstance(out, ShikimoriAnime)
        assert out.source_tag is not None
        assert out.source_tag.cached is False


class TestMangaRanobePeople:
    def test_manga_search_and_show_return_typed_rows(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("mangas_search/01-berserk.yaml"))
            _register(rsps, _load("mangas_by_id/01-berserk-2.yaml"))
            search = shiki_api.manga_search("Berserk", limit=2, no_cache=True)
            show = shiki_api.manga_show(2, no_cache=True)

        assert len(search) >= 1
        assert isinstance(search[0], ShikimoriManga)
        assert isinstance(show, ShikimoriManga)
        common = show.to_common()
        assert common.id == "shikimori:manga:2"
        assert common.format == "MANGA"

    def test_ranobe_search_and_show_return_typed_rows(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("ranobe_search/01-monogatari.yaml"))
            _register(rsps, _load("ranobe_by_id/01-monogatari-second-season-23751.yaml"))
            search = shiki_api.ranobe_search("Monogatari", limit=2, no_cache=True)
            show = shiki_api.ranobe_show(23751, no_cache=True)

        assert len(search) >= 1
        assert isinstance(search[0], ShikimoriManga)
        assert isinstance(show, ShikimoriManga)
        assert show.to_common().format == "NOVEL"

    def test_clubs_publishers_and_people_return_typed_rows(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("clubs_search/01-anime.yaml"))
            _register(rsps, _load("clubs_by_id/01-site-development-1.yaml"))
            _register(rsps, _load("publishers/01-all.yaml"))
            _register(rsps, _load("people_search/01-hayao-miyazaki.yaml"))
            _register(rsps, _load("people_by_id/01-hayao-miyazaki-1870.yaml"))
            clubs = shiki_api.club_search("anime", limit=3, no_cache=True)
            club = shiki_api.club_show(1, no_cache=True)
            publishers = shiki_api.publishers(no_cache=True)
            people = shiki_api.people_search("Hayao Miyazaki", no_cache=True)
            person = shiki_api.person(1870, no_cache=True)

        assert len(clubs) >= 1
        assert isinstance(clubs[0], ShikimoriClub)
        assert isinstance(club, ShikimoriClub)
        assert len(publishers) >= 1
        assert isinstance(publishers[0], ShikimoriPublisher)
        assert len(people) >= 1
        assert isinstance(people[0], ShikimoriPerson)
        assert isinstance(person, ShikimoriPerson)
        assert person.to_common().id == "shikimori:person:1870"


class TestCalendar:
    def test_calendar_returns_entries(self, fake_clock):
        fx = _load("calendar/01-limit-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.calendar(limit=1, no_cache=True)

        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriCalendarEntry)
        assert out[0].anime is not None

    def test_calendar_default_call_accepts_array_payload(self, fake_clock):
        fx = _load("calendar/16-default.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = shiki_api.calendar(no_cache=True)

        assert len(out) >= 1
        assert isinstance(out[0], ShikimoriCalendarEntry)


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


class TestErrorPaths:
    def test_429_raises_rate_limited(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991", status=429, body='{"message":"rate limited"}')
            with pytest.raises(ApiError) as ei:
                shiki_api.show(52991, no_cache=True)

        assert ei.value.backend == "shikimori"
        assert ei.value.reason == "rate-limited"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991", status=503, body='{"message":"unavailable"}')
            with pytest.raises(ApiError) as ei:
                shiki_api.show(52991, no_cache=True)

        assert ei.value.reason == "upstream-error"

    def test_non_text_body_raises_decode_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991", body=b"\xff", content_type="application/octet-stream")
            with pytest.raises(ApiError) as ei:
                shiki_api.show(52991, no_cache=True)

        assert ei.value.reason == "upstream-decode"

    def test_non_json_body_raises_decode_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991", body="<html />", content_type="text/html")
            with pytest.raises(ApiError) as ei:
                shiki_api.show(52991, no_cache=True)

        assert ei.value.reason == "upstream-decode"

    def test_show_array_payload_raises_shape_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991", body="[]")
            with pytest.raises(ApiError) as ei:
                shiki_api.show(52991, no_cache=True)

        assert ei.value.reason == "upstream-shape"

    @pytest.mark.parametrize(
        "fn,path,arg",
        [
            (shiki_api.manga_show, "/api/mangas/2", 2),
            (shiki_api.ranobe_show, "/api/ranobe/23751", 23751),
            (shiki_api.club_show, "/api/clubs/1", 1),
            (shiki_api.character, "/api/characters/184947", 184947),
            (shiki_api.person, "/api/people/1870", 1870),
        ],
    )
    def test_new_entity_show_array_payload_raises_shape_error(self, fake_clock, fn, path, arg):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register_path(rsps, path, body="[]")
            with pytest.raises(ApiError) as ei:
                fn(arg, no_cache=True)

        assert ei.value.backend == "shikimori"
        assert ei.value.reason == "upstream-shape"

    def test_null_list_payload_normalises_to_empty_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes", body="null")
            out = shiki_api.search("empty", no_cache=True)

        assert out == []

    def test_object_list_payload_normalises_to_one_row(self, fake_clock):
        body = '{"id":52991,"name":"Sousou no Frieren"}'
        with responses.RequestsMock() as rsps:
            _register_path(rsps, "/api/animes/52991/similar", body=body)
            out = shiki_api.similar(52991, no_cache=True)

        assert len(out) == 1
        assert isinstance(out[0], ShikimoriAnime)

    def test_publisher_not_found_raises_typed_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("publishers/01-all.yaml"))
            with pytest.raises(ApiError) as ei:
                shiki_api.publisher(999999999, no_cache=True)

        assert ei.value.backend == "shikimori"
        assert ei.value.reason == "not-found"

    def test_studio_not_found_raises_typed_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("studios/01-all.yaml"))
            with pytest.raises(ApiError) as ei:
                shiki_api.studio(999999999, no_cache=True)

        assert ei.value.backend == "shikimori"
        assert ei.value.reason == "not-found"
