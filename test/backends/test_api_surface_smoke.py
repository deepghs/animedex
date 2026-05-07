"""Smoke-coverage for every Python API function across the three
Phase-2 backends.

Each function is invoked once with a mocked dispatcher that returns
a minimal valid envelope. The test confirms the function body
parses + maps + raises typed errors correctly without 117 hand-
written cases.

The point isn't end-to-end correctness (that's covered by the
fixture-replay mapper tests); it's basic-execution coverage of every
public callable in the surface.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Dict

import pytest

from animedex.backends import anilist as anilist_api
from animedex.backends import jikan as jikan_api
from animedex.backends import trace as trace_api
from animedex.models.common import ApiError


pytestmark = pytest.mark.unittest


def _envelope_factory(body: dict, status: int = 200) -> Any:
    """Build a stub raw-dispatcher envelope returning ``body`` as
    JSON. Mirrors the shape of
    :class:`animedex.api._envelope.RawResponse` to the extent each
    Python API function inspects."""

    class _Env:
        firewall_rejected = None
        body_text = json.dumps(body)
        status = 200

        class cache:
            hit = False

        class timing:
            rate_limit_wait_ms = 0

    _Env.status = status
    return _Env()


# Minimal but valid envelope payload for each AniList query type.
# Populate at least one row per list-returning query so the mapper's
# row-projection branches actually execute (gives the smoke test
# real coverage, not just function-entry coverage).
ANILIST_PAYLOADS = {
    "show": {"data": {"Media": {"id": 1, "title": {"romaji": "x"}}}},
    "search": {"data": {"Page": {"pageInfo": {"total": 1}, "media": [{"id": 1, "title": {"romaji": "x"}}]}}},
    "character": {"data": {"Character": {"id": 1, "name": {"full": "x"}}}},
    "character_search": {
        "data": {"Page": {"pageInfo": {"total": 1}, "characters": [{"id": 1, "name": {"full": "x"}}]}},
    },
    "staff": {"data": {"Staff": {"id": 1, "name": {"full": "x"}}}},
    "staff_search": {
        "data": {"Page": {"pageInfo": {"total": 1}, "staff": [{"id": 1, "name": {"full": "x"}}]}},
    },
    "studio": {"data": {"Studio": {"id": 1, "name": "x"}}},
    "studio_search": {"data": {"Page": {"pageInfo": {"total": 1}, "studios": [{"id": 1, "name": "x"}]}}},
    "schedule": {"data": {"Page": {"pageInfo": {"total": 1}, "media": [{"id": 1, "title": {"romaji": "x"}}]}}},
    "trending": {"data": {"Page": {"media": [{"id": 1, "title": {"romaji": "x"}}]}}},
    "user": {
        "data": {
            "User": {
                "id": 1,
                "name": "x",
                "avatar": {"large": "u"},
                "siteUrl": "u",
                "statistics": {
                    "anime": {"count": 1, "meanScore": 90, "minutesWatched": 100},
                    "manga": {"count": 1, "meanScore": 80, "chaptersRead": 10},
                },
            }
        }
    },
    "user_search": {"data": {"Page": {"pageInfo": {"total": 1}, "users": [{"id": 1, "name": "x", "avatar": {"medium": "m"}}]}}},
    "genre_collection": {"data": {"GenreCollection": ["Action"]}},
    "media_tag_collection": {"data": {"MediaTagCollection": [{"id": 1, "name": "x"}]}},
    "site_statistics": {
        "data": {
            "SiteStatistics": {
                "users": {"nodes": [{"date": 0, "count": 1, "change": 0}]},
                "anime": {"nodes": [{"date": 0, "count": 1, "change": 0}]},
                "manga": {"nodes": []},
                "characters": {"nodes": []},
                "staff": {"nodes": []},
                "reviews": {"nodes": []},
            }
        }
    },
    "external_link_source_collection": {
        "data": {"ExternalLinkSourceCollection": [{"id": 1, "site": "Crunchyroll", "type": "STREAMING"}]},
    },
    "airing_schedule": {
        "data": {
            "Page": {
                "pageInfo": {"total": 1, "hasNextPage": False},
                "airingSchedules": [
                    {
                        "id": 1,
                        "airingAt": 0,
                        "episode": 1,
                        "timeUntilAiring": 0,
                        "media": {"id": 1, "title": {"romaji": "x"}},
                    }
                ],
            }
        }
    },
    "media_trend": {
        "data": {"Page": {"pageInfo": {"total": 1}, "mediaTrends": [{"date": 0, "trending": 0}]}},
    },
    "review": {
        "data": {
            "Page": {
                "pageInfo": {"total": 1},
                "reviews": [{"id": 1, "summary": "x", "score": 90, "user": {"name": "n"}}],
            }
        }
    },
    "recommendation": {
        "data": {
            "Page": {
                "pageInfo": {"total": 1},
                "recommendations": [
                    {
                        "id": 1,
                        "rating": 1,
                        "media": {"id": 1, "title": {"romaji": "x"}},
                        "mediaRecommendation": {"id": 2, "title": {"romaji": "y"}},
                    }
                ],
            }
        }
    },
    "thread": {
        "data": {
            "Page": {
                "threads": [
                    {"id": 1, "title": "t", "body": "b", "user": {"name": "u"}, "createdAt": 0}
                ]
            }
        }
    },
    "thread_comment": {
        "data": {"Page": {"threadComments": [{"id": 1, "comment": "c", "user": {"name": "u"}, "createdAt": 0}]}},
    },
    "activity": {
        "data": {
            "Page": {
                "activities": [
                    {"id": 1, "text": "t", "user": {"name": "u"}, "createdAt": 0},
                    {"id": 2, "status": "watched", "user": {"name": "u"}, "media": {"title": {"romaji": "x"}}, "createdAt": 0},
                ]
            }
        }
    },
    "activity_reply": {
        "data": {"Page": {"activityReplies": [{"id": 1, "text": "t", "user": {"name": "u"}, "createdAt": 0}]}},
    },
    "following": {"data": {"Page": {"following": [{"id": 1, "name": "x"}]}}},
    "follower": {"data": {"Page": {"followers": [{"id": 1, "name": "x"}]}}},
    "media_list_public": {
        "data": {
            "Page": {
                "mediaList": [
                    {"id": 1, "status": "CURRENT", "score": 9, "progress": 5, "media": {"id": 1, "title": {"romaji": "x"}}}
                ]
            }
        }
    },
    "media_list_collection_public": {
        "data": {
            "MediaListCollection": {
                "user": {"id": 1, "name": "x"},
                "lists": [{"name": "Watching", "status": "CURRENT", "entries": [{"id": 1}]}],
            }
        }
    },
}


# Function name → minimal kwargs that satisfy the signature.
ANILIST_KWARGS = {
    "show": {"id": 1},
    "search": {"q": "x"},
    "character": {"id": 1},
    "character_search": {"q": "x"},
    "staff": {"id": 1},
    "staff_search": {"q": "x"},
    "studio": {"id": 1},
    "studio_search": {"q": "x"},
    "schedule": {"year": 2026, "season": "FALL"},
    "trending": {},
    "user": {"name": "x"},
    "user_search": {"q": "x"},
    "genre_collection": {},
    "media_tag_collection": {},
    "site_statistics": {},
    "external_link_source_collection": {},
    "airing_schedule": {},
    "media_trend": {"media_id": 1},
    "review": {"media_id": 1},
    "recommendation": {"media_id": 1},
    "thread": {"q": "x"},
    "thread_comment": {"thread_id": 1},
    "activity": {},
    "activity_reply": {"activity_id": 1},
    "following": {"user_id": 1},
    "follower": {"user_id": 1},
    "media_list_public": {"user_name": "x"},
    "media_list_collection_public": {"user_name": "x"},
}


@pytest.mark.parametrize("fn_name", list(ANILIST_PAYLOADS.keys()))
def test_anilist_api_function_callable(fn_name, monkeypatch):
    """Each AniList Python function executes against a mocked
    dispatcher returning a minimal valid payload."""
    from animedex.api import anilist as raw

    payload = ANILIST_PAYLOADS[fn_name]
    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory(payload))

    fn = getattr(anilist_api, fn_name)
    kwargs = ANILIST_KWARGS[fn_name]
    fn(**kwargs)  # any successful return (single record OR list) counts


@pytest.mark.parametrize("fn_name", ["viewer", "notification", "ani_chart_user"])
def test_anilist_token_stubs_raise_auth_required(fn_name):
    fn = getattr(anilist_api, fn_name)
    with pytest.raises(ApiError) as exc_info:
        fn()
    assert exc_info.value.reason == "auth-required"


def test_anilist_markdown_stub_raises():
    with pytest.raises(ApiError) as exc_info:
        anilist_api.markdown("hello")
    assert exc_info.value.reason == "auth-required"


def test_anilist_search_with_invalid_season_raises():
    with pytest.raises(ApiError, match="unknown season"):
        anilist_api.schedule(2026, "INVALID")


# ---------- Jikan ----------


# Sub-set of Jikan functions that return rich typed dataclasses.
JIKAN_TYPED = {
    "show": ({"data": {"mal_id": 1, "title": "x"}}, {"mal_id": 1}),
    "manga_show": ({"data": {"mal_id": 1, "title": "x"}}, {"mal_id": 1}),
    "character_show": ({"data": {"mal_id": 1, "name": "x"}}, {"mal_id": 1}),
    "person_show": ({"data": {"mal_id": 1, "name": "x"}}, {"mal_id": 1}),
    "producer_show": ({"data": {"mal_id": 1}}, {"mal_id": 1}),
    "club_show": ({"data": {"mal_id": 1, "name": "x"}}, {"mal_id": 1}),
    "user_show": ({"data": {"username": "x"}}, {"username": "x"}),
    "user_basic": ({"data": {"username": "x"}}, {"username": "x"}),
    "random_anime": ({"data": {"mal_id": 1, "title": "x"}}, {}),
    "random_manga": ({"data": {"mal_id": 1, "title": "x"}}, {}),
    "random_character": ({"data": {"mal_id": 1, "name": "x"}}, {}),
    "random_person": ({"data": {"mal_id": 1, "name": "x"}}, {}),
    "random_user": ({"data": {"username": "x"}}, {}),
}


@pytest.mark.parametrize("fn_name", list(JIKAN_TYPED.keys()))
def test_jikan_typed_function_callable(fn_name, monkeypatch):
    from animedex.api import jikan as raw

    payload, kwargs = JIKAN_TYPED[fn_name]
    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory(payload))

    fn = getattr(jikan_api, fn_name)
    fn(**kwargs)


# Jikan list-returning functions
JIKAN_LIST = {
    "search": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "manga_search": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "character_search": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "person_search": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "producer_search": ({"data": [{"mal_id": 1}]}, {}),
    "magazines": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "genres_anime": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "genres_manga": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "clubs": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "seasons_now": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "seasons_upcoming": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "season": ({"data": [{"mal_id": 1, "title": "x"}]}, {"year": 2026, "season": "spring"}),
    "top_anime": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "top_manga": ({"data": [{"mal_id": 1, "title": "x"}]}, {}),
    "top_characters": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
    "top_people": ({"data": [{"mal_id": 1, "name": "x"}]}, {}),
}


@pytest.mark.parametrize("fn_name", list(JIKAN_LIST.keys()))
def test_jikan_list_function_callable(fn_name, monkeypatch):
    from animedex.api import jikan as raw

    payload, kwargs = JIKAN_LIST[fn_name]
    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory(payload))
    fn = getattr(jikan_api, fn_name)
    fn(**kwargs)


# Jikan generic-envelope functions (the long tail)
JIKAN_GENERIC: Dict[str, Dict[str, Any]] = {
    "anime_characters": {"mal_id": 1},
    "anime_staff": {"mal_id": 1},
    "anime_episodes": {"mal_id": 1},
    "anime_episode": {"mal_id": 1, "episode": 1},
    "anime_news": {"mal_id": 1},
    "anime_forum": {"mal_id": 1},
    "anime_videos": {"mal_id": 1},
    "anime_videos_episodes": {"mal_id": 1},
    "anime_pictures": {"mal_id": 1},
    "anime_statistics": {"mal_id": 1},
    "anime_moreinfo": {"mal_id": 1},
    "anime_recommendations": {"mal_id": 1},
    "anime_userupdates": {"mal_id": 1},
    "anime_reviews": {"mal_id": 1},
    "anime_relations": {"mal_id": 1},
    "anime_themes": {"mal_id": 1},
    "anime_external": {"mal_id": 1},
    "anime_streaming": {"mal_id": 1},
    "manga_characters": {"mal_id": 1},
    "manga_news": {"mal_id": 1},
    "manga_forum": {"mal_id": 1},
    "manga_pictures": {"mal_id": 1},
    "manga_statistics": {"mal_id": 1},
    "manga_moreinfo": {"mal_id": 1},
    "manga_recommendations": {"mal_id": 1},
    "manga_userupdates": {"mal_id": 1},
    "manga_reviews": {"mal_id": 1},
    "manga_relations": {"mal_id": 1},
    "manga_external": {"mal_id": 1},
    "character_anime": {"mal_id": 1},
    "character_manga": {"mal_id": 1},
    "character_voices": {"mal_id": 1},
    "character_pictures": {"mal_id": 1},
    "person_anime": {"mal_id": 1},
    "person_voices": {"mal_id": 1},
    "person_manga": {"mal_id": 1},
    "person_pictures": {"mal_id": 1},
    "producer_external": {"mal_id": 1},
    "club_members": {"mal_id": 1},
    "club_staff": {"mal_id": 1},
    "club_relations": {"mal_id": 1},
    "user_statistics": {"username": "x"},
    "user_favorites": {"username": "x"},
    "user_userupdates": {"username": "x"},
    "user_about": {"username": "x"},
    "user_history": {"username": "x"},
    "user_friends": {"username": "x"},
    "user_reviews": {"username": "x"},
    "user_recommendations": {"username": "x"},
    "user_clubs": {"username": "x"},
    "user_search": {},
    "user_by_mal_id": {"mal_id": 1},
    "seasons_list": {},
    "top_reviews": {},
    "schedules": {},
    "recommendations_anime": {},
    "recommendations_manga": {},
    "reviews_anime": {},
    "reviews_manga": {},
    "watch_episodes": {},
    "watch_episodes_popular": {},
    "watch_promos": {},
    "watch_promos_popular": {},
}


@pytest.mark.parametrize("fn_name", list(JIKAN_GENERIC.keys()))
def test_jikan_generic_function_callable(fn_name, monkeypatch):
    from animedex.api import jikan as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"data": [], "pagination": {}}))
    fn = getattr(jikan_api, fn_name)
    fn(**JIKAN_GENERIC[fn_name])


def test_jikan_404_raises_not_found(monkeypatch):
    from animedex.api import jikan as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"status": 404}, status=404))
    with pytest.raises(ApiError) as exc_info:
        jikan_api.show(99999999)
    assert exc_info.value.reason == "not-found"


def test_jikan_500_raises_upstream_error(monkeypatch):
    from animedex.api import jikan as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"status": 500}, status=500))
    with pytest.raises(ApiError) as exc_info:
        jikan_api.show(1)
    assert exc_info.value.reason == "upstream-error"


# ---------- Trace ----------


def test_trace_search_with_url_callable(monkeypatch):
    from animedex.api import trace as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"result": []}))
    hits = trace_api.search(image_url="https://example.invalid/x.jpg")
    assert hits == []


def test_trace_search_with_bytes_callable(monkeypatch):
    from animedex.api import trace as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"result": []}))
    hits = trace_api.search(raw_bytes=b"\xff\xd8\xff\xe0")
    assert hits == []


def test_trace_search_with_full_options(monkeypatch):
    from animedex.api import trace as raw

    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory({"result": []}))
    trace_api.search(
        image_url="https://example.invalid/x.jpg",
        anilist_info=True,
        cut_borders=True,
        anilist_id=154587,
    )


def test_trace_search_hit_with_inline_anilist_title(monkeypatch):
    from animedex.api import trace as raw

    payload = {
        "result": [
            {
                "anilist": {
                    "id": 1,
                    "title": {"romaji": "x", "english": "X", "native": "x"},
                },
                "similarity": 0.95,
                "episode": 1,
                "from": 0.0,
                "at": 0.5,
                "to": 1.0,
                "filename": "x.mkv",
                "duration": 1500.0,
                "video": "https://x.invalid/v",
                "image": "https://x.invalid/i",
            }
        ]
    }
    monkeypatch.setattr(raw, "call", lambda **kw: _envelope_factory(payload))
    hits = trace_api.search(image_url="https://example.invalid/x.jpg", anilist_info=True)
    assert len(hits) == 1
    assert hits[0].anilist_title is not None
    assert hits[0].anilist_title.romaji == "x"


# ---------- API surface coverage check ----------


def test_anilist_module_surface_has_no_drift():
    """Ensure the smoke-coverage table covers every public function on
    the AniList Python module (modulo selftest + auth-required stubs)."""
    public = {
        name
        for name, value in inspect.getmembers(anilist_api)
        if inspect.isfunction(value) and not name.startswith("_") and value.__module__ == "animedex.backends.anilist"
    }
    auth_stubs = {"viewer", "notification", "markdown", "ani_chart_user"}
    excluded = {"selftest"} | auth_stubs
    covered = set(ANILIST_PAYLOADS.keys())
    missing = public - excluded - covered
    assert not missing, f"AniList API drift; uncovered functions: {sorted(missing)}"


def test_jikan_module_surface_has_no_drift():
    public = {
        name
        for name, value in inspect.getmembers(jikan_api)
        if inspect.isfunction(value) and not name.startswith("_") and value.__module__ == "animedex.backends.jikan"
    }
    excluded = {"selftest"}
    covered = set(JIKAN_TYPED) | set(JIKAN_LIST) | set(JIKAN_GENERIC)
    missing = public - excluded - covered
    assert not missing, f"Jikan API drift; uncovered functions: {sorted(missing)}"
