"""Tests for :mod:`animedex.backends.kitsu` (the high-level Python API).

Per AGENTS §9bis: only HTTP transport is mocked; the real
dispatcher / cache / rate-limit / firewall stack runs end-to-end.
Each test loads a captured fixture, registers it with
``responses``, calls the public function, and asserts on the
return shape and the cross-source projection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import kitsu as kitsu_api
from animedex.backends.kitsu.models import (
    KitsuAnime,
    KitsuAnimeAttributes,
    KitsuCategory,
    KitsuCharacter,
    KitsuFranchise,
    KitsuGenre,
    KitsuManga,
    KitsuMangaAttributes,
    KitsuMapping,
    KitsuPerson,
    KitsuProducer,
    KitsuRelatedResource,
    KitsuStreamer,
    KitsuStreamingLinkAttributes,
    KitsuStreamingLink,
    KitsuUser,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "kitsu"


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
    """Register a fixture under URL-path-with-optional-query matching."""
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


class TestShow:
    def test_show_returns_typed_anime_resource(self, fake_clock):
        fx = _load("anime_by_id/01-frieren-46474.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.show(46474, no_cache=True)
        assert isinstance(out, KitsuAnime)
        assert out.id == "46474"
        assert out.type == "anime"
        assert out.attributes is not None
        assert out.attributes.canonicalTitle is not None
        assert out.source_tag is not None
        assert out.source_tag.backend == "kitsu"

    def test_show_to_common_projects_to_anime(self, fake_clock):
        from animedex.models.anime import Anime, AnimeRating

        fx = _load("anime_by_id/01-frieren-46474.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.show(46474, no_cache=True)
        common = out.to_common()
        assert isinstance(common, Anime)
        assert common.id == "kitsu:46474"
        assert "Frieren" in (common.title.romaji or "") or "Sousou" in (common.title.romaji or "")
        assert isinstance(common.score, AnimeRating)


class TestSearch:
    def test_search_returns_list_of_typed_anime(self, fake_clock):
        fx = _load("anime_search/01-frieren.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.search("Frieren", limit=5, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, KitsuAnime)


class TestStreaming:
    def test_streaming_returns_typed_links(self, fake_clock):
        fx = _load("anime_streaming_links/01-frieren-46474.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.streaming(46474, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, KitsuStreamingLink)
            assert row.attributes is not None
            assert row.attributes.url is not None
            common = row.to_common()
            assert common.url == row.attributes.url
            assert common.provider != "unknown" or row.attributes.url is None


class TestMappings:
    def test_mappings_returns_external_ids(self, fake_clock):
        fx = _load("anime_mappings/01-frieren-46474.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.mappings(46474, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, KitsuMapping)
            assert row.attributes is not None
            assert row.attributes.externalSite is not None
            assert row.attributes.externalId is not None


class TestTrending:
    def test_trending_returns_list_of_anime(self, fake_clock):
        fx = _load("trending_anime/01-top10.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.trending(limit=10, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, KitsuAnime)


class TestManga:
    def test_manga_show(self, fake_clock):
        from animedex.models.manga import Manga

        fx = _load("manga_by_id/01-berserk-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.manga_show(1, no_cache=True)
        assert isinstance(out, KitsuManga)
        assert out.id == "1"
        common = out.to_common()
        assert isinstance(common, Manga)
        assert common.id == "kitsu:1"

    def test_manga_search(self, fake_clock):
        fx = _load("manga_search/01-berserk.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.manga_search("Berserk", limit=5, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, KitsuManga)


class TestCategories:
    def test_categories_returns_typed_rows(self, fake_clock):
        fx = _load("categories/01-top20.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = kitsu_api.categories(limit=20, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, KitsuCategory)


_KITSU_ANIME_RELATION_WRAPPERS = [
    ("anime_characters", "anime_characters/01-frieren.yaml", KitsuRelatedResource),
    ("anime_staff", "anime_staff/01-frieren.yaml", KitsuRelatedResource),
    ("anime_episodes", "anime_episodes/01-frieren.yaml", KitsuRelatedResource),
    ("anime_reviews", "anime_reviews/01-frieren.yaml", KitsuRelatedResource),
    ("anime_genres", "anime_genres/01-frieren.yaml", KitsuGenre),
    ("anime_categories", "anime_categories/01-frieren.yaml", KitsuCategory),
    ("anime_relations", "anime_relations/01-frieren.yaml", KitsuRelatedResource),
    ("anime_productions", "anime_productions/01-frieren.yaml", KitsuRelatedResource),
]

_KITSU_MANGA_RELATION_WRAPPERS = [
    ("manga_characters", "manga_characters/01-berserk.yaml", KitsuRelatedResource),
    ("manga_staff", "manga_staff/01-berserk.yaml", KitsuRelatedResource),
    ("manga_chapters", "manga_chapters/01-berserk.yaml", KitsuRelatedResource),
    ("manga_genres", "manga_genres/01-berserk.yaml", KitsuGenre),
]

_KITSU_SHOW_WRAPPERS = [
    ("character", "characters_by_id/01-edward-elric-1.yaml", KitsuCharacter),
    ("person", "people_by_id/01-miyazaki-1.yaml", KitsuPerson),
    ("producer", "producers_by_id/01-id-1.yaml", KitsuProducer),
    ("genre", "genres_by_id/01-id-1.yaml", KitsuGenre),
    ("category", "categories_by_id/01-id-1.yaml", KitsuCategory),
    ("franchise", "franchises_by_id/01-id-1.yaml", KitsuFranchise),
    ("user", "users_by_id/01-id-1.yaml", KitsuUser),
]

_KITSU_LIST_WRAPPERS = [
    ("character_search", "characters/01-page1.yaml", KitsuCharacter),
    ("person_search", "people/01-page1.yaml", KitsuPerson),
    ("producers", "producers/01-page1.yaml", KitsuProducer),
    ("genres", "genres/01-page1.yaml", KitsuGenre),
    ("streamers", "streamers/01-all.yaml", KitsuStreamer),
    ("franchises", "franchises/01-page1.yaml", KitsuFranchise),
    ("trending_manga", "trending_manga/01-top10.yaml", KitsuManga),
]


@pytest.mark.parametrize("fn_name,fixture_rel,expected_type", _KITSU_ANIME_RELATION_WRAPPERS)
def test_anime_relation_wrappers_return_typed_lists(fn_name, fixture_rel, expected_type, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        rows = getattr(kitsu_api, fn_name)(46474, no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, expected_type)


@pytest.mark.parametrize("fn_name,fixture_rel,expected_type", _KITSU_MANGA_RELATION_WRAPPERS)
def test_manga_relation_wrappers_return_typed_lists(fn_name, fixture_rel, expected_type, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        rows = getattr(kitsu_api, fn_name)(1, no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, expected_type)


@pytest.mark.parametrize("fn_name,fixture_rel,expected_type", _KITSU_SHOW_WRAPPERS)
def test_singleton_wrappers_return_typed_resources(fn_name, fixture_rel, expected_type, fake_clock):
    fx = _load(fixture_rel)
    rec_id = int(fx["response"]["body_json"]["data"]["id"])
    with responses.RequestsMock() as rsps:
        _register(rsps, fx)
        row = getattr(kitsu_api, fn_name)(rec_id, no_cache=True)
    assert isinstance(row, expected_type)


@pytest.mark.parametrize("fn_name,fixture_rel,expected_type", _KITSU_LIST_WRAPPERS)
def test_collection_wrappers_return_typed_lists(fn_name, fixture_rel, expected_type, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        rows = getattr(kitsu_api, fn_name)(no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, expected_type)


@pytest.mark.parametrize(
    "fn_name,fixture_rel",
    [
        ("person_voices", "people_voices/01-person-1.yaml"),
        ("person_castings", "people_castings/01-person-1.yaml"),
    ],
)
def test_person_credit_wrappers_return_related_resources(fn_name, fixture_rel, fake_clock):
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(fixture_rel))
        rows = getattr(kitsu_api, fn_name)(1, no_cache=True)
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, KitsuRelatedResource)


class TestUsers:
    def test_user_library_returns_related_resources(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_library_entries/01-user-1.yaml"))
            rows = kitsu_api.user_library(1, no_cache=True)
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, KitsuRelatedResource)

    def test_user_stats_returns_related_resources(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("users_stats/01-user-1.yaml"))
            rows = kitsu_api.user_stats(1, no_cache=True)
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, KitsuRelatedResource)


class TestKitsuBoundaryBranches:
    def test_listing_none_data_returns_empty_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://kitsu.io/api/edge/characters", json={"data": None}, status=200)
            rows = kitsu_api.character_search(no_cache=True)
        assert rows == []

    def test_listing_single_data_object_is_wrapped(self, fake_clock):
        body = {"data": {"id": "1", "type": "characters", "attributes": {"name": "Edward Elric"}}}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://kitsu.io/api/edge/characters", json=body, status=200)
            rows = kitsu_api.character_search(no_cache=True)
        assert len(rows) == 1
        assert isinstance(rows[0], KitsuCharacter)

    def test_character_search_with_query_threads_filter(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("characters/01-page1.yaml"))
            rows = kitsu_api.character_search("edward", no_cache=True)
            sent = rsps.calls[0].request
        assert isinstance(rows, list)
        assert "filter%5Bname%5D=edward" in sent.url

    def test_person_search_with_query_threads_filter(self, fake_clock):
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("people/01-page1.yaml"))
            rows = kitsu_api.person_search("miyazaki", no_cache=True)
            sent = rsps.calls[0].request
        assert isinstance(rows, list)
        assert "filter%5Bname%5D=miyazaki" in sent.url

    def test_model_projection_fallbacks(self):
        from animedex.models.anime import Anime
        from animedex.models.manga import Manga

        anime = KitsuAnime(
            id="x",
            attributes=KitsuAnimeAttributes(titles={"en_jp": "Fallback"}, startDate=None, status=None),
        ).to_common()
        assert isinstance(anime, Anime)
        assert anime.source.backend == "kitsu"
        assert anime.season_year is None
        assert anime.status is None

        manga = KitsuManga(
            id="m",
            attributes=KitsuMangaAttributes(titles={"en_jp": "Fallback"}, status=None, mangaType=None),
        ).to_common()
        assert isinstance(manga, Manga)
        assert manga.status is None
        assert manga.format is None

        unknown = KitsuStreamingLink(id="s", attributes=KitsuStreamingLinkAttributes(url=None)).to_common()
        assert unknown.provider == "unknown"
        custom = KitsuStreamingLink(
            id="s", attributes=KitsuStreamingLinkAttributes(url="https://video.example.invalid/x")
        ).to_common()
        assert custom.provider == "video.example.invalid"


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_unknown_id_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://kitsu.io/api/edge/anime/999999999",
                json={"errors": [{"title": "Record not found"}]},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                kitsu_api.show(999999999, no_cache=True)
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://kitsu.io/api/edge/anime/46474",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                kitsu_api.show(46474, no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://kitsu.io/api/edge/anime/46474",
                body="<html>oops</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                kitsu_api.show(46474, no_cache=True)
        assert ei.value.reason == "upstream-decode"

    def test_missing_data_key_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://kitsu.io/api/edge/anime/46474",
                json={"oops": "no data key"},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                kitsu_api.show(46474, no_cache=True)
        assert ei.value.reason == "upstream-shape"


# ---------- selftest ----------


def test_module_selftest_returns_true():
    """The high-level module's offline ``selftest()`` must pass."""
    assert kitsu_api.selftest() is True


def test_models_selftest_returns_true():
    from animedex.backends.kitsu import models

    assert models.selftest() is True
