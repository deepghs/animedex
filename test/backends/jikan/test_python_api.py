"""Happy-path tests for every public function in :mod:`animedex.backends.jikan`.

Drives the full Python API through the real dispatcher + fixture-replay
HTTP layer (only HTTP transport is mocked, per AGENTS §9bis.5). Each
case maps a fixture folder to the Python API call that produces its
URL; the parametrised test loads the first fixture, registers it with
``responses``, calls the function, and asserts the return shape.

Goal: lift coverage of ``animedex/backends/jikan/__init__.py`` from
~46% to >95% — the parametrised body exercises every wrapper that
otherwise has no direct caller in the suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Tuple

import pytest
import responses
import yaml

from animedex.backends import jikan as jikan_api
from animedex.backends.jikan.models import (
    JikanAnime,
    JikanCharacter,
    JikanClub,
    JikanGenericResponse,
    JikanGenre,
    JikanManga,
    JikanPerson,
    JikanProducer,
    JikanUser,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "jikan"


@pytest.fixture
def fake_clock(monkeypatch):
    """Freeze the ratelimit + cache clocks (AGENTS §9bis.5: HTTP-adjacent
    only — clocks, not project logic)."""
    state = {"rl_now": 0.0, "cache_now": datetime(2026, 5, 7, tzinfo=timezone.utc)}
    monkeypatch.setattr("animedex.transport.ratelimit._monotonic", lambda: state["rl_now"])
    monkeypatch.setattr(
        "animedex.transport.ratelimit._sleep",
        lambda s: state.update({"rl_now": state["rl_now"] + s}),
    )
    monkeypatch.setattr("animedex.cache.sqlite._utcnow", lambda: state["cache_now"])
    return state


def _load_first_fixture(folder: str) -> dict:
    """Load the alphabetically-first YAML fixture in
    ``test/fixtures/jikan/<folder>/``."""
    files = sorted((FIXTURES / folder).glob("*.yaml"))
    if not files:
        pytest.skip(f"no fixture in {folder}")
    return yaml.safe_load(files[0].read_text(encoding="utf-8"))


def _register(rsps: responses.RequestsMock, fixture: dict) -> None:
    """Register a fixture for replay, matching ONLY on URL-path.

    The shared :func:`register_fixture_with_responses` matches strict
    query strings, but our happy-path table calls the function with
    its own default kwargs (``page=1``, etc.) that the captured
    fixture URL may or may not carry. For coverage purposes the path
    is the canonical key; query-string drift is a separate concern."""
    import re
    from urllib.parse import urlsplit
    from tools.fixtures.capture import fixture_response_bytes

    req = fixture["request"]
    resp = fixture["response"]
    body = fixture_response_bytes(fixture)
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
            body=body,
        )
    )


# ---------- The case table ----------
#
# Each entry: (fixture_folder, callable, args, kwargs, expected_type_or_check)
#
# The IDs encoded in args (52991, 2, 11, 1, 1870, 17, "nekomata1037", 39)
# match the IDs used when the fixture corpus was captured — see the URL
# audit: ``test/fixtures/jikan/anime_full/01-frieren-52991.yaml`` URL
# is ``/anime/52991/full``, so ``show(52991)`` is the call.

CASES: List[Tuple[str, Callable, tuple, dict, Any]] = [
    # ---------- /anime/{id}/... ----------
    ("anime_full", jikan_api.show, (52991,), {}, JikanAnime),
    ("anime_search", jikan_api.search, ("Frieren",), {"limit": 3, "type": "tv"}, list),
    ("anime_characters", jikan_api.anime_characters, (52991,), {}, JikanGenericResponse),
    ("anime_staff", jikan_api.anime_staff, (52991,), {}, JikanGenericResponse),
    ("anime_episodes", jikan_api.anime_episodes, (52991,), {}, JikanGenericResponse),
    ("anime_news", jikan_api.anime_news, (52991,), {}, JikanGenericResponse),
    ("anime_forum", jikan_api.anime_forum, (52991,), {"filter": "all"}, JikanGenericResponse),
    ("anime_videos", jikan_api.anime_videos, (52991,), {}, JikanGenericResponse),
    ("anime_videos_episodes", jikan_api.anime_videos_episodes, (52991,), {}, JikanGenericResponse),
    ("anime_pictures", jikan_api.anime_pictures, (52991,), {}, JikanGenericResponse),
    ("anime_statistics", jikan_api.anime_statistics, (52991,), {}, JikanGenericResponse),
    ("anime_moreinfo", jikan_api.anime_moreinfo, (52991,), {}, JikanGenericResponse),
    ("anime_recommendations", jikan_api.anime_recommendations, (52991,), {}, JikanGenericResponse),
    ("anime_userupdates", jikan_api.anime_userupdates, (52991,), {}, JikanGenericResponse),
    ("anime_reviews", jikan_api.anime_reviews, (52991,), {}, JikanGenericResponse),
    ("anime_relations", jikan_api.anime_relations, (52991,), {}, JikanGenericResponse),
    ("anime_themes", jikan_api.anime_themes, (52991,), {}, JikanGenericResponse),
    ("anime_external", jikan_api.anime_external, (52991,), {}, JikanGenericResponse),
    ("anime_streaming", jikan_api.anime_streaming, (52991,), {}, JikanGenericResponse),
    # ---------- /manga/{id}/... ----------
    ("manga_full", jikan_api.manga_show, (2,), {}, JikanManga),
    ("manga_search", jikan_api.manga_search, ("Berserk",), {"limit": 3}, list),
    ("manga_characters", jikan_api.manga_characters, (2,), {}, JikanGenericResponse),
    ("manga_news", jikan_api.manga_news, (2,), {}, JikanGenericResponse),
    ("manga_forum", jikan_api.manga_forum, (2,), {}, JikanGenericResponse),
    ("manga_pictures", jikan_api.manga_pictures, (2,), {}, JikanGenericResponse),
    ("manga_statistics", jikan_api.manga_statistics, (2,), {}, JikanGenericResponse),
    ("manga_moreinfo", jikan_api.manga_moreinfo, (2,), {}, JikanGenericResponse),
    ("manga_recommendations", jikan_api.manga_recommendations, (2,), {}, JikanGenericResponse),
    ("manga_userupdates", jikan_api.manga_userupdates, (2,), {}, JikanGenericResponse),
    ("manga_reviews", jikan_api.manga_reviews, (2,), {}, JikanGenericResponse),
    ("manga_relations", jikan_api.manga_relations, (2,), {}, JikanGenericResponse),
    ("manga_external", jikan_api.manga_external, (2,), {}, JikanGenericResponse),
    # ---------- /characters/{id}/... ----------
    ("characters_full", jikan_api.character_show, (11,), {}, JikanCharacter),
    ("characters_search", jikan_api.character_search, ("Frieren",), {"limit": 3}, list),
    ("characters_anime", jikan_api.character_anime, (11,), {}, JikanGenericResponse),
    ("characters_manga", jikan_api.character_manga, (11,), {}, JikanGenericResponse),
    ("characters_voices", jikan_api.character_voices, (11,), {}, JikanGenericResponse),
    ("characters_pictures", jikan_api.character_pictures, (11,), {}, JikanGenericResponse),
    # ---------- /people/{id}/... ----------
    ("people_full", jikan_api.person_show, (1870,), {}, JikanPerson),
    ("people_search", jikan_api.person_search, ("Miyazaki",), {"limit": 3}, list),
    ("people_anime", jikan_api.person_anime, (1870,), {}, JikanGenericResponse),
    ("people_voices", jikan_api.person_voices, (1870,), {}, JikanGenericResponse),
    ("people_manga", jikan_api.person_manga, (1870,), {}, JikanGenericResponse),
    ("people_pictures", jikan_api.person_pictures, (1870,), {}, JikanGenericResponse),
    # ---------- /producers/{id}/... ----------
    ("producers_full", jikan_api.producer_show, (17,), {}, JikanProducer),
    ("producers_search", jikan_api.producer_search, ("Aniplex",), {}, list),
    ("producers_external", jikan_api.producer_external, (17,), {}, JikanGenericResponse),
    # ---------- /magazines + /genres ----------
    ("magazines_list", jikan_api.magazines, ("Shonen",), {"limit": 3}, list),
    ("genres_anime", jikan_api.genres_anime, (), {}, list),
    ("genres_manga", jikan_api.genres_manga, (), {}, list),
    # ---------- /clubs ----------
    ("clubs_search", jikan_api.clubs, ("fma",), {"limit": 3}, JikanGenericResponse),
    ("clubs_by_id", jikan_api.club_show, (1,), {}, JikanClub),
    ("clubs_members", jikan_api.club_members, (1,), {}, JikanGenericResponse),
    ("clubs_staff", jikan_api.club_staff, (1,), {}, JikanGenericResponse),
    ("clubs_relations", jikan_api.club_relations, (1,), {}, JikanGenericResponse),
    # ---------- /users ----------
    ("users_full", jikan_api.user_show, ("nekomata1037",), {}, JikanUser),
    ("users_by_name", jikan_api.user_basic, ("nekomata1037",), {}, JikanUser),
    ("users_statistics", jikan_api.user_statistics, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_favorites", jikan_api.user_favorites, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_userupdates", jikan_api.user_userupdates, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_about", jikan_api.user_about, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_history", jikan_api.user_history, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_friends", jikan_api.user_friends, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_reviews", jikan_api.user_reviews, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_recommendations", jikan_api.user_recommendations, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_clubs", jikan_api.user_clubs, ("nekomata1037",), {}, JikanGenericResponse),
    ("users_search", jikan_api.user_search, ("nekomata",), {"limit": 3}, JikanGenericResponse),
    ("users_userbyid", jikan_api.user_by_mal_id, (39,), {}, JikanGenericResponse),
    # ---------- /seasons ----------
    ("seasons_list", jikan_api.seasons_list, (), {}, JikanGenericResponse),
    ("seasons_now", jikan_api.seasons_now, (), {"limit": 10}, list),
    ("seasons_upcoming", jikan_api.seasons_upcoming, (), {"limit": 5}, list),
    ("seasons", jikan_api.season, (2023, "fall"), {"limit": 3}, list),
    # ---------- /top ----------
    ("top_anime", jikan_api.top_anime, (), {"limit": 10}, list),
    ("top_manga", jikan_api.top_manga, (), {"limit": 5}, list),
    ("top_characters", jikan_api.top_characters, (), {"limit": 5}, list),
    ("top_people", jikan_api.top_people, (), {"limit": 5}, list),
    ("top_reviews", jikan_api.top_reviews, (), {"type": "anime"}, JikanGenericResponse),
    # ---------- /schedules ----------
    ("schedules", jikan_api.schedules, (), {"filter": "monday", "limit": 5}, JikanGenericResponse),
    # ---------- /random ----------
    ("random_anime", jikan_api.random_anime, (), {}, JikanAnime),
    ("random_manga", jikan_api.random_manga, (), {}, JikanManga),
    ("random_characters", jikan_api.random_character, (), {}, JikanCharacter),
    ("random_people", jikan_api.random_person, (), {}, JikanPerson),
    ("random_users", jikan_api.random_user, (), {}, JikanUser),
    # ---------- /recommendations + /reviews ----------
    ("recommendations_anime", jikan_api.recommendations_anime, (), {}, JikanGenericResponse),
    ("recommendations_manga", jikan_api.recommendations_manga, (), {}, JikanGenericResponse),
    ("reviews_anime", jikan_api.reviews_anime, (), {}, JikanGenericResponse),
    ("reviews_manga", jikan_api.reviews_manga, (), {}, JikanGenericResponse),
    # ---------- /watch ----------
    ("watch_episodes", jikan_api.watch_episodes, (), {}, JikanGenericResponse),
    ("watch_episodes_popular", jikan_api.watch_episodes_popular, (), {}, JikanGenericResponse),
    ("watch_promos", jikan_api.watch_promos, (), {}, JikanGenericResponse),
    ("watch_promos_popular", jikan_api.watch_promos_popular, (), {}, JikanGenericResponse),
]


@pytest.mark.parametrize(
    "folder,fn,args,kwargs,expected",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_jikan_api_round_trip(folder, fn, args, kwargs, expected, fake_clock):
    """Drive ``fn(*args, **kwargs)`` through the real dispatcher with the
    captured fixture replayed by ``responses``.

    A handful of fixtures captured a 5xx/404 from a flaky upstream
    (clubs/users/reviews endpoints were misbehaving the day capture
    ran). For those, the contract is ``ApiError``; the function-call
    path runs the same code, just exits via the error branch. This
    still exercises the wrapper, so coverage holds."""
    from animedex.models.common import ApiError

    fixture = _load_first_fixture(folder)
    captured_status = fixture["response"]["status"]

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _register(rsps, fixture)
        if captured_status >= 400:
            with pytest.raises(ApiError):
                fn(*args, no_cache=True, **kwargs)
            return
        result = fn(*args, no_cache=True, **kwargs)

    if expected is list:
        assert isinstance(result, list)
    else:
        assert isinstance(result, expected), (
            f"{fn.__name__}({args}, {kwargs}): expected {expected.__name__}, got {type(result).__name__}"
        )


# ---------- Edge cases for _fetch error paths ----------


class TestErrorPaths:
    """Coverage for the error branches in ``_fetch`` / ``_data`` /
    ``_generic`` that the happy-path table doesn't exercise."""

    def test_404_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/999999999/full",
                json={"status": 404, "type": "BadResponseException", "message": "Resource does not exist"},
                status=404,
            )
            with pytest.raises(ApiError) as exc_info:
                jikan_api.show(999999999, no_cache=True)
        assert exc_info.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/clubs",
                json={"error": "internal"},
                status=500,
            )
            with pytest.raises(ApiError) as exc_info:
                jikan_api.clubs("anything", no_cache=True)
        assert exc_info.value.reason == "upstream-error"

    def test_missing_data_key_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/52991/full",
                json={"unexpected": "shape"},
                status=200,
            )
            with pytest.raises(ApiError) as exc_info:
                jikan_api.show(52991, no_cache=True)
        assert exc_info.value.reason == "upstream-shape"

    def test_generic_with_dict_data_wraps_to_list(self, fake_clock):
        """When Jikan returns ``data: {<single-row>}`` instead of a list,
        ``_generic`` must wrap it. This is the dict-not-list branch."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/52991/moreinfo",
                json={"data": {"moreinfo": "Some plot summary"}},
                status=200,
            )
            result = jikan_api.anime_moreinfo(52991, no_cache=True)
        assert isinstance(result, JikanGenericResponse)
        assert len(result.rows) == 1

    def test_generic_with_scalar_data_wraps(self, fake_clock):
        """When Jikan returns ``data: <scalar>``, ``_generic`` wraps it
        into ``{"value": <scalar>}``. Exercises the scalar branch."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/52991/moreinfo",
                json={"data": "raw_string_payload"},
                status=200,
            )
            result = jikan_api.anime_moreinfo(52991, no_cache=True)
        assert isinstance(result, JikanGenericResponse)
        assert len(result.rows) == 1

    def test_firewall_branch(self, fake_clock, monkeypatch):
        """Exercise the ``firewall_rejected`` short-circuit in
        ``_fetch``. The read-only firewall fires on mutating methods,
        not GET, so we monkey-patch the per-backend ``call`` to return
        a duck-typed envelope with ``firewall_rejected`` set. AGENTS
        §9bis.5 allows monkey-patching the dispatcher for tests of the
        dispatcher's own behaviour; here we're testing ``_fetch``'s
        branching on the dispatcher's contract."""
        from animedex.api import jikan as raw_jikan
        from animedex.models.common import ApiError
        from types import SimpleNamespace

        def _stub_call(*, path, params=None, config=None, **kw):
            return SimpleNamespace(
                firewall_rejected={"reason": "read-only", "message": "blocked"},
                body_text="",
                status=0,
                cache=SimpleNamespace(hit=False),
                timing=SimpleNamespace(rate_limit_wait_ms=0),
            )

        monkeypatch.setattr(raw_jikan, "call", _stub_call)
        with pytest.raises(ApiError) as exc_info:
            jikan_api.show(52991, no_cache=True)
        assert exc_info.value.reason == "read-only"

    def test_body_text_none_branch(self, fake_clock, monkeypatch):
        """``_fetch`` raises ``upstream-decode`` when the dispatcher
        couldn't decode the body to text."""
        from animedex.api import jikan as raw_jikan
        from animedex.models.common import ApiError
        from types import SimpleNamespace

        def _stub_call(*, path, params=None, config=None, **kw):
            return SimpleNamespace(
                firewall_rejected=None,
                body_text=None,
                status=200,
                cache=SimpleNamespace(hit=False),
                timing=SimpleNamespace(rate_limit_wait_ms=0),
            )

        monkeypatch.setattr(raw_jikan, "call", _stub_call)
        with pytest.raises(ApiError) as exc_info:
            jikan_api.show(52991, no_cache=True)
        assert exc_info.value.reason == "upstream-decode"


# ---------- Extra coverage: branches the canonical fixtures miss ----------


class TestSearchConditionalParams:
    """``jikan.search`` adds optional query params only when the caller
    sets them. Exercise each branch."""

    @pytest.fixture
    def stub_search_endpoint(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime",
                json={"data": [], "pagination": {}},
                status=200,
            )
            yield rsps

    def test_search_with_status(self, stub_search_endpoint):
        result = jikan_api.search("Frieren", status="airing", no_cache=True)
        assert isinstance(result, list)

    def test_search_with_rating(self, stub_search_endpoint):
        jikan_api.search("Frieren", rating="pg13", no_cache=True)

    def test_search_with_sfw_true(self, stub_search_endpoint):
        jikan_api.search("Frieren", sfw=True, no_cache=True)

    def test_search_with_sfw_false(self, stub_search_endpoint):
        jikan_api.search("Frieren", sfw=False, no_cache=True)

    def test_search_with_genres(self, stub_search_endpoint):
        jikan_api.search("Frieren", genres="1,2", no_cache=True)

    def test_search_with_order_by_and_sort(self, stub_search_endpoint):
        jikan_api.search("Frieren", order_by="score", sort="desc", no_cache=True)


class TestReviewsConditionalParams:
    """``jikan.anime_reviews`` adds optional ``preliminary`` /
    ``spoilers`` params when set."""

    @pytest.fixture
    def stub_reviews_endpoint(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/52991/reviews",
                json={"data": [], "pagination": {}},
                status=200,
            )
            yield rsps

    def test_reviews_preliminary_true(self, stub_reviews_endpoint):
        jikan_api.anime_reviews(52991, preliminary=True, no_cache=True)

    def test_reviews_preliminary_false(self, stub_reviews_endpoint):
        jikan_api.anime_reviews(52991, preliminary=False, no_cache=True)

    def test_reviews_spoilers_true(self, stub_reviews_endpoint):
        jikan_api.anime_reviews(52991, spoilers=True, no_cache=True)

    def test_reviews_spoilers_false(self, stub_reviews_endpoint):
        jikan_api.anime_reviews(52991, spoilers=False, no_cache=True)


class TestTopAnimeConditionalParams:
    """``jikan.top_anime`` carries optional ``type`` / ``filter``."""

    @pytest.fixture
    def stub_top_anime(self, fake_clock):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/top/anime",
                json={"data": []},
                status=200,
            )
            yield rsps

    def test_top_anime_with_type(self, stub_top_anime):
        jikan_api.top_anime(type="tv", no_cache=True)

    def test_top_anime_with_filter(self, stub_top_anime):
        jikan_api.top_anime(filter="airing", no_cache=True)


class TestEndpointsBlockedByFlakyCaptureFixtures:
    """A few endpoints ship only 5xx-status fixtures (clubs, certain
    user paths, etc.). Drive the happy path with a synthetic 200
    response so the wrapper code lights up."""

    def test_anime_episode_single(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/anime/52991/episodes/1",
                json={"data": {"mal_id": 1, "title": "Episode 1"}},
                status=200,
            )
            result = jikan_api.anime_episode(52991, 1, no_cache=True)
        assert isinstance(result, JikanGenericResponse)

    def test_clubs_search_happy(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/clubs",
                json={"data": [{"mal_id": 1, "name": "FMA Club"}], "pagination": {}},
                status=200,
            )
            result = jikan_api.clubs("fma", no_cache=True)
        assert isinstance(result, list)
        assert isinstance(result[0], JikanClub)

    def test_clubs_no_query(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/clubs",
                json={"data": [], "pagination": {}},
                status=200,
            )
            jikan_api.clubs(no_cache=True)

    def test_club_show_happy(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/clubs/1",
                json={"data": {"mal_id": 1, "name": "FMA Club"}},
                status=200,
            )
            result = jikan_api.club_show(1, no_cache=True)
        assert isinstance(result, JikanClub)

    def test_genres_with_filter(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/genres/anime",
                json={"data": [{"mal_id": 1, "name": "Action"}]},
                status=200,
            )
            result = jikan_api.genres_anime(filter="genres", no_cache=True)
        assert isinstance(result, list)
        assert isinstance(result[0], JikanGenre)

    def test_top_reviews_with_type(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.jikan.moe/v4/top/reviews",
                json={"data": [{"mal_id": 1}], "pagination": {}},
                status=200,
            )
            jikan_api.top_reviews(type="anime", no_cache=True)


class TestSelftest:
    """The :func:`jikan.selftest` callable is a 100-line public-callable
    list — registering it covers a large block of the module."""

    def test_selftest_returns_true(self):
        assert jikan_api.selftest() is True


# Several wrappers can only get coverage on their happy-path
# ``return _generic(...)`` line via a synthetic 200 response, because
# the fixture captured 5xx the day it ran. Each row: (function, args,
# stub-URL).
HAPPY_PATH_STUBS: List[Tuple[Callable, tuple, str]] = [
    (jikan_api.anime_news, (52991,), "https://api.jikan.moe/v4/anime/52991/news"),
    (jikan_api.anime_userupdates, (52991,), "https://api.jikan.moe/v4/anime/52991/userupdates"),
    (jikan_api.manga_moreinfo, (2,), "https://api.jikan.moe/v4/manga/2/moreinfo"),
    (jikan_api.club_members, (1,), "https://api.jikan.moe/v4/clubs/1/members"),
    (jikan_api.club_staff, (1,), "https://api.jikan.moe/v4/clubs/1/staff"),
    (jikan_api.user_history, ("nekomata1037",), "https://api.jikan.moe/v4/users/nekomata1037/history"),
    (jikan_api.user_friends, ("nekomata1037",), "https://api.jikan.moe/v4/users/nekomata1037/friends"),
    (jikan_api.user_reviews, ("nekomata1037",), "https://api.jikan.moe/v4/users/nekomata1037/reviews"),
    (jikan_api.user_recommendations, ("nekomata1037",), "https://api.jikan.moe/v4/users/nekomata1037/recommendations"),
    (jikan_api.user_clubs, ("nekomata1037",), "https://api.jikan.moe/v4/users/nekomata1037/clubs"),
    (jikan_api.user_by_mal_id, (39,), "https://api.jikan.moe/v4/users/userbyid/39"),
    (jikan_api.reviews_manga, (), "https://api.jikan.moe/v4/reviews/manga"),
]


@pytest.mark.parametrize(
    "fn,args,url",
    HAPPY_PATH_STUBS,
    ids=[case[0].__name__ for case in HAPPY_PATH_STUBS],
)
def test_happy_path_stubbed_200(fn, args, url, fake_clock):
    """Cover the ``return _generic(payload, src)`` line for endpoints
    whose canonical fixture captured a 5xx."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(responses.GET, url, json={"data": [], "pagination": {}}, status=200)
        result = fn(*args, no_cache=True)
    assert isinstance(result, JikanGenericResponse)


# ---------- JikanAnime model helpers ----------


class TestParseHelpers:
    """``JikanAnime`` ships static parse-helpers that the canonical
    Frieren fixture exercises only one branch of. Hit the others."""

    def test_parse_duration_minutes_hr_min(self):
        assert JikanAnime._parse_duration_minutes("1 hr 30 min per ep") == 90

    def test_parse_duration_minutes_hr_only(self):
        assert JikanAnime._parse_duration_minutes("2 hr") == 120

    def test_parse_duration_minutes_min_only(self):
        assert JikanAnime._parse_duration_minutes("24 min per ep") == 24

    def test_parse_duration_minutes_unparseable(self):
        assert JikanAnime._parse_duration_minutes("unknown") is None

    def test_parse_duration_minutes_empty(self):
        assert JikanAnime._parse_duration_minutes(None) is None
        assert JikanAnime._parse_duration_minutes("") is None

    def test_parse_iso_date_ok(self):
        result = JikanAnime._parse_iso_date("2023-09-29T17:00:00+00:00")
        assert result is not None and result.year == 2023

    def test_parse_iso_date_with_z(self):
        result = JikanAnime._parse_iso_date("2024-03-22T17:00:00Z")
        assert result is not None and result.month == 3

    def test_parse_iso_date_garbage(self):
        assert JikanAnime._parse_iso_date("not-a-date") is None

    def test_parse_iso_date_empty(self):
        assert JikanAnime._parse_iso_date(None) is None

    @pytest.mark.parametrize(
        "s,expected",
        [
            ("Currently Airing", "airing"),
            ("Finished Airing", "finished"),
            ("Not yet aired", "upcoming"),
            ("Cancelled", "cancelled"),
            ("Canceled", "cancelled"),
            ("On Hiatus", "hiatus"),
            ("Mystery State", "unknown"),
            ("", None),
            (None, None),
        ],
    )
    def test_normalise_status(self, s, expected):
        assert JikanAnime._normalise_status(s) == expected

    @pytest.mark.parametrize(
        "s,expected",
        [
            ("TV", "TV"),
            ("Movie", "MOVIE"),
            ("OVA", "OVA"),
            ("ONA", "ONA"),
            ("Special", "SPECIAL"),
            ("Music", "MUSIC"),
            ("TV Short", "TV_SHORT"),
            ("Random Format", None),
            (None, None),
            ("", None),
        ],
    )
    def test_normalise_format(self, s, expected):
        assert JikanAnime._normalise_format(s) == expected


class TestCharacterToCommonBranches:
    """``JikanCharacter.to_common`` picks the MAIN role when present
    and falls back to the first non-MAIN. Exercise both paths."""

    def _make_character(self, anime_roles):
        return JikanCharacter.model_validate(
            {
                "mal_id": 1,
                "name": "Test",
                "anime": anime_roles,
                "manga": [],
                "voices": [],
                "source_tag": {
                    "backend": "jikan",
                    "fetched_at": datetime(2026, 5, 7, tzinfo=timezone.utc),
                },
            }
        )

    def test_main_role_wins(self):
        c = self._make_character(
            [
                {"role": "Supporting", "anime": {"mal_id": 1, "url": "x", "images": {}, "title": "x"}},
                {"role": "Main", "anime": {"mal_id": 2, "url": "x", "images": {}, "title": "x"}},
            ]
        )
        common = c.to_common()
        assert common.role == "Main"

    def test_supporting_only(self):
        c = self._make_character(
            [
                {"role": "Supporting", "anime": {"mal_id": 1, "url": "x", "images": {}, "title": "x"}},
            ]
        )
        common = c.to_common()
        assert common.role == "Supporting"

    def test_no_anime_roles(self):
        c = self._make_character([])
        common = c.to_common()
        assert common.role is None


class TestModelsSelftest:
    """``animedex.backends.jikan.models.selftest`` rolls every dataclass
    through validate-dump-validate."""

    def test_models_selftest(self):
        from animedex.backends.jikan import models as jikan_models

        assert jikan_models.selftest() is True
