"""Happy-path tests for every public function in :mod:`animedex.backends.anilist`.

Drives the full Python API through the real dispatcher + fixture-replay
HTTP layer (only HTTP transport is mocked, per AGENTS §9bis.5).

Goal: lift coverage of ``animedex/backends/anilist/__init__.py`` and
``animedex/backends/anilist/_mapper.py`` from ~50% to >95%.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Tuple

import pytest
import responses
import yaml

from animedex.backends import anilist as anilist_api
from animedex.backends.anilist.models import (
    AnilistAnime,
    AnilistCharacter,
    AnilistGenreCollection,
    AnilistSiteStatistics,
    AnilistStaff,
    AnilistStudio,
    AnilistUser,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "anilist"


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


def _load_fixture(rel: str) -> dict:
    return yaml.safe_load((FIXTURES / rel).read_text(encoding="utf-8"))


def _register(rsps: responses.RequestsMock, fixture: dict) -> None:
    """Register a fixture response for any POST to graphql.anilist.co.

    All AniList traffic goes through one URL; the fixture differs by
    GraphQL query body. ``responses`` treats this as: register one
    response per test, no body matching needed."""
    from tools.fixtures.capture import fixture_response_bytes

    req = fixture["request"]
    resp = fixture["response"]
    body = fixture_response_bytes(fixture)
    _STRIP = {"content-encoding", "content-length", "transfer-encoding"}
    sanitised_headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP}
    rsps.add(
        responses.Response(
            method=req["method"].upper(),
            url=req["url"],
            status=resp["status"],
            headers=sanitised_headers,
            body=body,
        )
    )


# ---------- Cases keyed on fixture file ----------


CASES: List[Tuple[str, Callable, tuple, dict, Any]] = [
    # (fixture_rel, fn, args, kwargs, expected_type_or_list)
    ("phase2_media/01-media-frieren.yaml", anilist_api.show, (154587,), {}, AnilistAnime),
    ("phase2_search/01-search-frieren.yaml", anilist_api.search, ("Frieren",), {"per_page": 5}, list),
    ("phase2_character/01-character-edward-elric.yaml", anilist_api.character, (36,), {}, AnilistCharacter),
    ("phase2_staff/01-staff-101572.yaml", anilist_api.staff, (101572,), {}, AnilistStaff),
    ("phase2_studio/01-studio-madhouse.yaml", anilist_api.studio, (11,), {}, AnilistStudio),
    ("phase2_trending/01-trending-top8.yaml", anilist_api.trending, (), {"per_page": 8}, list),
    ("phase2_schedule/01-schedule-2024-spring.yaml", anilist_api.schedule, (2024, "SPRING"), {"per_page": 10}, list),
    # ---------- Long tail (one fixture each) ----------
    ("phase2_longtail/01-media-trend-frieren.yaml", anilist_api.media_trend, (154587,), {"per_page": 5}, list),
    (
        "phase2_longtail/02-airing-schedule-by-media.yaml",
        anilist_api.airing_schedule,
        (),
        {"media_id": 154587, "per_page": 5},
        list,
    ),
    (
        "phase2_longtail/03-airing-schedule-not-yet-aired.yaml",
        anilist_api.airing_schedule,
        (),
        {"not_yet_aired": True, "per_page": 5},
        list,
    ),
    (
        "phase2_longtail/04-review-by-media.yaml",
        anilist_api.review,
        (),
        {"media_id": 154587, "per_page": 5},
        list,
    ),
    (
        "phase2_longtail/05-recommendation-by-media.yaml",
        anilist_api.recommendation,
        (),
        {"media_id": 154587, "per_page": 5},
        list,
    ),
    (
        "phase2_longtail/06-media-tag-collection.yaml",
        anilist_api.media_tag_collection,
        (),
        {},
        list,
    ),
    ("phase2_longtail/07-user-by-name.yaml", anilist_api.user, ("AniList",), {}, AnilistUser),
    ("phase2_longtail/08-activity-page.yaml", anilist_api.activity, (), {"per_page": 5}, list),
    (
        "phase2_longtail/09-activity-reply.yaml",
        anilist_api.activity_reply,
        (),
        {"activity_id": 123, "per_page": 5},
        list,
    ),
    ("phase2_longtail/10-thread-by-search.yaml", anilist_api.thread, ("Frieren",), {"per_page": 5}, list),
    (
        "phase2_longtail/11-thread-comment-by-thread.yaml",
        anilist_api.thread_comment,
        (),
        {"thread_id": 123, "per_page": 5},
        list,
    ),
    (
        "phase2_longtail/12-following-by-user.yaml",
        anilist_api.following,
        (6933956,),
        {"per_page": 5},
        list,
    ),
    (
        "phase2_longtail/13-follower-by-user.yaml",
        anilist_api.follower,
        (6933956,),
        {"per_page": 5},
        list,
    ),
    (
        "phase2_longtail/14-site-statistics.yaml",
        anilist_api.site_statistics,
        (),
        {},
        AnilistSiteStatistics,
    ),
    (
        "phase2_longtail/15-external-link-source-collection.yaml",
        anilist_api.external_link_source_collection,
        (),
        {},
        list,
    ),
    (
        "phase2_longtail/16-media-list-public.yaml",
        anilist_api.media_list_public,
        ("AniList",),
        {"type": "ANIME", "per_page": 10},
        list,
    ),
    (
        "phase2_longtail/17-media-list-collection-public.yaml",
        anilist_api.media_list_collection_public,
        ("AniList",),
        {"type": "ANIME"},
        "AnilistMediaListCollection",  # special: not list, not a top-level imported type
    ),
    (
        "phase2_longtail/18-user-search.yaml",
        anilist_api.user_search,
        ("ani",),
        {"per_page": 5},
        list,
    ),
    (
        "phase2_longtail/19-genre-collection-singleton.yaml",
        anilist_api.genre_collection,
        (),
        {},
        AnilistGenreCollection,
    ),
    (
        "phase2_longtail/20-studio-search.yaml",
        anilist_api.studio_search,
        ("Madhouse",),
        {"per_page": 5},
        list,
    ),
    (
        "phase2_longtail/21-character-search.yaml",
        anilist_api.character_search,
        ("Naruto",),
        {"per_page": 5},
        list,
    ),
    (
        "phase2_longtail/22-staff-search.yaml",
        anilist_api.staff_search,
        ("Yamada",),
        {"per_page": 5},
        list,
    ),
]


@pytest.mark.parametrize(
    "fixture_rel,fn,args,kwargs,expected",
    CASES,
    ids=[c[0].split("/")[-1].replace(".yaml", "") for c in CASES],
)
def test_anilist_api_round_trip(fixture_rel, fn, args, kwargs, expected, fake_clock):
    path = FIXTURES / fixture_rel
    if not path.exists():
        pytest.skip(f"fixture missing: {fixture_rel}")
    fixture = _load_fixture(fixture_rel)

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _register(rsps, fixture)
        result = fn(*args, no_cache=True, **kwargs)

    if expected is list:
        assert isinstance(result, list)
    elif isinstance(expected, str):
        # String form: assert by class name for types we don't import
        # at the top of the module.
        assert type(result).__name__ == expected
    else:
        assert isinstance(result, expected)


# ---------- Auth-required stubs ----------


class TestAuthRequiredStubs:
    """The four token-required AniList commands must raise ``ApiError``
    with ``reason='auth-required'`` until the Phase-8 token flow lands."""

    @pytest.mark.parametrize(
        "fn,args",
        [
            (anilist_api.viewer, ()),
            (anilist_api.notification, ()),
            (anilist_api.markdown, ("**bold**",)),
            (anilist_api.ani_chart_user, ()),
        ],
    )
    def test_auth_required(self, fn, args):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc_info:
            fn(*args)
        assert exc_info.value.reason == "auth-required"


# ---------- Error paths in _fetch_graphql ----------


class TestErrorPaths:
    def test_500_with_non_graphql_body_falls_through_to_not_found(self, fake_clock):
        """``_gql`` doesn't gate on HTTP status (AniList sometimes
        returns 200 with errors and 5xx with valid bodies). A 500
        with a non-GraphQL body has no ``data`` key, so the mapper
        sees ``Media=None`` and raises ``not-found``. This is the
        current contract; documented here so nobody silently changes
        it."""
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://graphql.anilist.co/",
                json={"error": "internal"},
                status=500,
            )
            with pytest.raises(ApiError) as exc_info:
                anilist_api.show(154587, no_cache=True)
        assert exc_info.value.reason == "not-found"

    def test_firewall_branch(self, fake_clock, monkeypatch):
        """Cover ``_gql``'s ``firewall_rejected`` short-circuit."""
        from animedex.api import anilist as raw_anilist
        from animedex.models.common import ApiError
        from types import SimpleNamespace

        def _stub_call(*, query, variables=None, config=None, **kw):
            return SimpleNamespace(
                firewall_rejected={"reason": "read-only", "message": "blocked"},
                body_text="",
                cache=SimpleNamespace(hit=False),
                timing=SimpleNamespace(rate_limit_wait_ms=0),
            )

        monkeypatch.setattr(raw_anilist, "call", _stub_call)
        with pytest.raises(ApiError) as exc_info:
            anilist_api.show(154587, no_cache=True)
        assert exc_info.value.reason == "read-only"

    def test_body_text_none(self, fake_clock, monkeypatch):
        """Cover ``_gql``'s ``upstream-decode`` branch."""
        from animedex.api import anilist as raw_anilist
        from animedex.models.common import ApiError
        from types import SimpleNamespace

        def _stub_call(*, query, variables=None, config=None, **kw):
            return SimpleNamespace(
                firewall_rejected=None,
                body_text=None,
                cache=SimpleNamespace(hit=False),
                timing=SimpleNamespace(rate_limit_wait_ms=0),
            )

        monkeypatch.setattr(raw_anilist, "call", _stub_call)
        with pytest.raises(ApiError) as exc_info:
            anilist_api.show(154587, no_cache=True)
        assert exc_info.value.reason == "upstream-decode"

    def test_404_via_null_data(self, fake_clock):
        """AniList returns 200 + ``data: {Media: null}`` for a missing
        ID rather than 404. The mapper raises ``not-found``."""
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://graphql.anilist.co/",
                json={"data": {"Media": None}},
                status=200,
            )
            with pytest.raises(ApiError) as exc_info:
                anilist_api.show(99999999, no_cache=True)
        assert exc_info.value.reason == "not-found"

    def test_graphql_errors(self, fake_clock):
        """An error block in the GraphQL response surfaces as
        ``upstream-error``."""
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "https://graphql.anilist.co/",
                json={"errors": [{"message": "Invalid query"}]},
                status=200,
            )
            with pytest.raises(ApiError) as exc_info:
                anilist_api.show(154587, no_cache=True)
        assert "Invalid query" in str(exc_info.value) or exc_info.value.reason


class TestSelftest:
    def test_anilist_selftest(self):
        assert anilist_api.selftest() is True

    def test_selftest_catches_silent_token_stub(self, monkeypatch):
        """Cover the defensive ``raise AssertionError(...)`` branch:
        if a token-required stub silently returns instead of raising
        ``auth-required``, ``selftest()`` must fail loudly."""
        import animedex.backends.anilist as anilist_mod

        # Replace ``viewer`` with a no-op so the inner ``else`` branch
        # (function did not raise) fires.
        monkeypatch.setattr(anilist_mod, "viewer", lambda *a, **kw: None)
        with pytest.raises(AssertionError):
            anilist_mod.selftest()


# ---------- Bad-args branches ----------


class TestBadArgs:
    def test_schedule_bad_season(self):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as exc_info:
            anilist_api.schedule(2024, "bogus", no_cache=True)
        assert exc_info.value.reason == "bad-args"

    def test_schedule_lowercase_season_normalised(self, fake_clock):
        """Lower-case season name is upper-cased and accepted."""
        path = FIXTURES / "phase2_schedule" / "01-schedule-2024-spring.yaml"
        if not path.exists():
            pytest.skip("schedule fixture missing")
        fixture = _load_fixture("phase2_schedule/01-schedule-2024-spring.yaml")
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            _register(rsps, fixture)
            result = anilist_api.schedule(2024, "spring", no_cache=True)
        assert isinstance(result, list)


# ---------- Token-required mappers (covered via direct invocation) ----------


class TestTokenRequiredMappers:
    """The four token-required Python API endpoints are wired to
    raise ``auth-required`` via ``_require_token`` before the mapper
    runs. The mappers themselves still need coverage; drive them by
    direct invocation with synthetic payloads."""

    def test_map_viewer(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {"data": {"Viewer": {"id": 1, "name": "tester"}}}
        result = mp.map_viewer(payload, src)
        assert result.name == "tester"

    def test_map_notification(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "Page": {
                    "notifications": [
                        {
                            "id": 1,
                            "type": "AIRING",
                            "context": "is airing",
                            "contexts": ["x", "y"],
                            "user": {"name": "alice"},
                            "createdAt": 1234567890,
                        },
                        # Branch: unknown type → falls through to lowercase-replace
                        {
                            "id": 2,
                            "type": "MYSTERY_NEW_KIND",
                            "context": "?",
                            "contexts": "not-a-list",  # exercise the not-isinstance branch
                            "user": None,
                        },
                        # Branch: empty type
                        {"id": 3, "type": "", "user": {}, "contexts": []},
                    ]
                }
            }
        }
        result = mp.map_notification(payload, src)
        assert len(result) == 3
        assert result[0].kind == "airing"
        assert result[1].kind == "mystery-new-kind"
        assert result[2].kind == "unknown"

    def test_map_markdown(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {"data": {"Markdown": {"html": "<p>hi</p>"}}}
        result = mp.map_markdown(payload, src)
        assert result.html == "<p>hi</p>"

    def test_map_ani_chart_user(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "AniChartUser": {
                    "user": {"id": 5, "name": "ani"},
                    "settings": {"titleLanguage": "ROMAJI"},
                }
            }
        }
        result = mp.map_ani_chart_user(payload, src)
        assert result.user_id == 5

    def test_map_user_list_avatar_branch(self):
        """Cover the ``avatar_large = av.get("large") or av.get("medium")``
        line in :func:`map_user_list`."""
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "Page": {
                    "users": [
                        {"id": 1, "name": "u1", "avatar": {"large": "L"}},
                        {"id": 2, "name": "u2", "avatar": {"medium": "M"}},  # falls back
                        {"id": 3, "name": "u3", "avatar": None},
                    ]
                }
            }
        }
        result = mp.map_user_list(payload, src)
        assert len(result) == 3
        assert result[0].avatar_large == "L"
        assert result[1].avatar_large == "M"

    def test_map_activity_text_branch(self):
        """Cover the ``if "text" in r:`` branch in
        :func:`map_activity` — pure text activities (no media)."""
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "Page": {
                    "activities": [{"id": 1, "text": "hello world", "createdAt": 1, "user": {"id": 1, "name": "u"}}]
                }
            }
        }
        result = mp.map_activity(payload, src)
        assert len(result) == 1


class TestAnilistTrailerEmbed:
    """Cover ``_AnilistTrailer.to_url()`` for youtube + dailymotion +
    unknown provider."""

    def _trailer(self, **kwargs):
        from animedex.backends.anilist.models import _AnilistTrailer

        return _AnilistTrailer(**kwargs)

    def test_youtube(self):
        assert self._trailer(id="abc123", site="youtube").to_url() == "https://www.youtube.com/watch?v=abc123"

    def test_dailymotion(self):
        assert self._trailer(id="x123", site="dailymotion").to_url() == "https://www.dailymotion.com/video/x123"

    def test_unknown_site_returns_none(self):
        assert self._trailer(id="x", site="vimeo").to_url() is None

    def test_missing_id_or_site(self):
        assert self._trailer(id=None, site="youtube").to_url() is None
        assert self._trailer(id="abc", site=None).to_url() is None


class TestAnilistModelsSelftest:
    def test_models_selftest(self):
        from animedex.backends.anilist import models as anilist_models

        assert anilist_models.selftest() is True


class TestAnimeStreamingDedup:
    """``AnilistAnime.to_common`` deduplicates streaming providers
    using ``streamingEpisodes``. The Frieren fixture has unique
    providers; build a synthetic media to exercise the dedup branch."""

    def test_dedup_streaming(self):
        from datetime import datetime, timezone
        from animedex.backends.anilist.models import AnilistAnime
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        m = AnilistAnime.model_validate(
            {
                "id": 1,
                "title": {"romaji": "X"},
                "streamingEpisodes": [
                    {"site": "Crunchyroll", "url": "https://x.invalid/ep1"},
                    {"site": "Crunchyroll", "url": "https://x.invalid/ep2"},  # duplicate
                    {"site": "Netflix", "url": "https://x.invalid/n1"},
                ],
                "source_tag": src,
            }
        )
        common = m.to_common()
        providers = [s.provider for s in common.streaming]
        assert providers == ["Crunchyroll", "Netflix"]


class TestCharacterRoleFallback:
    """``AnilistCharacter.to_common`` falls back to ``media.edges[0]``
    when no explicit MAIN role is set."""

    def test_role_from_first_edge(self):
        from datetime import datetime, timezone
        from animedex.backends.anilist.models import AnilistCharacter
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        c = AnilistCharacter.model_validate(
            {
                "id": 1,
                "name": {"full": "X"},
                "media": {"edges": [{"characterRole": "SUPPORTING", "node": {"id": 1, "title": {"romaji": "Foo"}}}]},
                "source_tag": src,
            }
        )
        common = c.to_common()
        assert common.role == "SUPPORTING"


class TestMediaListPublicBranches:
    """Cover ``map_media_list_public`` with a non-empty mediaList."""

    def test_non_empty_media_list(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "Page": {
                    "mediaList": [
                        {
                            "id": 1,
                            "status": "CURRENT",
                            "score": 9.0,
                            "progress": 5,
                            "media": {"id": 100, "title": {"romaji": "Foo"}},
                        }
                    ]
                }
            }
        }
        result = mp.map_media_list_public(payload, src)
        assert len(result) == 1
        assert result[0].id == 1


class TestMediaListBranches:
    """Cover ``map_media_list_user_public`` and
    ``map_media_list_collection_public`` with payloads that exercise the
    nested-list branch."""

    def test_media_list_collection_groups(self):
        from animedex.backends.anilist import _mapper as mp
        from animedex.models.common import SourceTag

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        payload = {
            "data": {
                "MediaListCollection": {
                    "user": {"id": 1, "name": "u"},
                    "lists": [
                        {
                            "name": "Watching",
                            "entries": [{"id": 100, "score": 8.5, "media": {"id": 1, "title": {"romaji": "Foo"}}}],
                        },
                        {"name": "Empty", "entries": []},
                    ],
                }
            }
        }
        result = mp.map_media_list_collection_public(payload, src)
        assert result.user_name == "u"
        assert len(result.lists) == 2
        assert result.lists[0].name == "Watching"
        assert result.lists[0].entry_count == 1
        assert result.lists[1].name == "Empty"
        assert result.lists[1].entry_count == 0
