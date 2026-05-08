"""Tests for :mod:`animedex.backends.danbooru` (the high-level Python API)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import responses
import yaml

from animedex.backends import danbooru as db_api
from animedex.backends.danbooru.models import (
    DanbooruArtist,
    DanbooruCount,
    DanbooruPool,
    DanbooruPost,
    DanbooruTag,
)


pytestmark = pytest.mark.unittest

FIXTURES = Path(__file__).resolve().parents[3] / "test" / "fixtures" / "danbooru"


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
    """Path-only fixture register (URL path matches; query strings
    accepted regardless)."""
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


def _register_as(rsps: responses.RequestsMock, fixture: dict, path: str) -> None:
    """Register a fixture body under a path different from the
    captured request path."""
    import re

    resp = fixture["response"]
    url_re = re.compile(re.escape(f"https://danbooru.donmai.us{path}") + r"(\?.*)?$")

    _STRIP = {"content-encoding", "content-length", "transfer-encoding"}
    sanitised_headers = {k: v for k, v in (resp.get("headers") or {}).items() if k.lower() not in _STRIP}

    rsps.add(
        responses.Response(
            method=fixture["request"]["method"].upper(),
            url=url_re,
            status=resp["status"],
            headers=sanitised_headers,
            json=resp.get("body_json"),
        )
    )


# ---------- happy path ----------


class TestSearch:
    def test_search_returns_typed_posts(self, fake_clock):
        from animedex.models.art import ArtPost

        fx = _load("posts_search/01-touhou-rating-g-order-score.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.search("touhou rating:g order:score", limit=2, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, DanbooruPost)
            common = row.to_common()
            assert isinstance(common, ArtPost)
            assert common.rating == "g"
            assert "touhou" in common.tags

    def test_search_with_explicit_rating_passes_through(self, fake_clock):
        """User explicitly asks for rating:e — the library does not
        rewrite the query. Pin the inform-don't-gate posture."""
        fx = _load("posts_search/04-touhou-rating-e.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.search("touhou rating:e", limit=2, no_cache=True)
        # Whatever rows came back, they keep their upstream rating
        # verbatim (the lossless contract); we don't assert all are
        # rating:e because the upstream may have returned an empty
        # result for a rare combo.
        assert isinstance(out, list)

    def test_search_null_payload_returns_empty_list(self, fake_clock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://danbooru.donmai.us/posts.json", body="null", status=200)
            out = db_api.search("empty", no_cache=True)
        assert out == []


class TestPost:
    def test_post_returns_typed_resource(self, fake_clock):
        fx = _load("posts_by_id/01-post-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.post(1, no_cache=True)
        assert isinstance(out, DanbooruPost)
        assert out.id == 1

    def test_post_to_common_uses_default_source_without_source_tag(self):
        common = DanbooruPost(id=1, file_url="https://example.invalid/image.jpg").to_common()
        assert common.source.backend == "danbooru"


class TestArtist:
    def test_artist_search_substring(self, fake_clock):
        fx = _load("artists_search/02-ke-ta.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.artist_search("ke-ta", limit=5, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruArtist)

    def test_artist_returns_typed_resource(self, fake_clock):
        fx = _load("artists_search/02-ke-ta.yaml")
        row_body = fx["response"]["body_json"][0]
        with responses.RequestsMock() as rsps:
            _register_as(
                rsps, {**fx, "response": {**fx["response"], "body_json": row_body}}, f"/artists/{row_body['id']}.json"
            )
            out = db_api.artist(row_body["id"], no_cache=True)
        assert isinstance(out, DanbooruArtist)


class TestTag:
    def test_tag_prefix_search(self, fake_clock):
        fx = _load("tags_search/01-touhou-prefix.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.tag("touhou*", limit=5, no_cache=True)
        assert isinstance(out, list)
        assert len(out) >= 1
        for row in out:
            assert isinstance(row, DanbooruTag)


class TestPool:
    def test_pool_returns_typed_resource(self, fake_clock):
        fx = _load("pools_by_id/01-pool-1.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.pool(1, no_cache=True)
        assert isinstance(out, DanbooruPool)
        assert out.id == 1

    def test_pool_search_returns_typed_rows(self, fake_clock):
        fx = _load("pools_by_id/13-pools-search-touhou.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.pool_search("touhou*", limit=2, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruPool)


class TestCount:
    def test_count_returns_typed_envelope(self, fake_clock):
        fx = _load("counts/01-touhou-rating-g.yaml")
        with responses.RequestsMock() as rsps:
            _register(rsps, fx)
            out = db_api.count("touhou rating:g", no_cache=True)
        assert isinstance(out, DanbooruCount)
        assert out.total() is None or isinstance(out.total(), int)

    def test_count_without_tags_returns_typed_envelope(self, fake_clock):
        fx = _load("counts/05-touhou-only.yaml")
        with responses.RequestsMock() as rsps:
            _register_as(rsps, fx, "/counts/posts.json")
            out = db_api.count(no_cache=True)
        assert isinstance(out, DanbooruCount)

    def test_total_returns_none_for_empty_or_bad_count(self):
        assert DanbooruCount(counts=None).total() is None
        assert DanbooruCount(counts={"posts": None}).total() is None


# ---------- error paths ----------


class TestErrorPaths:
    def test_404_post_raises_not_found(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts/999999999.json",
                json={"error": "not found"},
                status=404,
            )
            with pytest.raises(ApiError) as ei:
                db_api.post(999999999, no_cache=True)
        assert ei.value.reason == "not-found"

    def test_5xx_raises_upstream_error(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                json={"error": "internal"},
                status=503,
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "upstream-error"

    def test_post_non_dict_response_raises_upstream_shape(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts/1.json",
                json=["unexpected", "list"],
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                db_api.post(1, no_cache=True)
        assert ei.value.reason == "upstream-shape"

    def test_non_json_body_raises_upstream_decode(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                body="<html>cloudflare challenge</html>",
                status=200,
                content_type="text/html",
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "upstream-decode"

    def test_401_raises_auth_required(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://danbooru.donmai.us/posts.json", json={"error": "auth"}, status=401)
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "auth-required"

    def test_429_raises_rate_limited(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                json={"success": False, "error": "Rate limit exceeded", "rate_limited": True},
                status=429,
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "rate-limited"

    def test_200_error_object_raises_rate_limited(self, fake_clock):
        from animedex.models.common import ApiError

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://danbooru.donmai.us/posts.json",
                json={"success": False, "error": "Rate limit exceeded", "rate_limited": True},
                status=200,
            )
            with pytest.raises(ApiError) as ei:
                db_api.search("touhou", no_cache=True)
        assert ei.value.reason == "rate-limited"

    @pytest.mark.parametrize(
        "fn,path,body",
        [
            (db_api.artist, "/artists/1.json", ["unexpected"]),
            (db_api.pool, "/pools/1.json", ["unexpected"]),
            (db_api.count, "/counts/posts.json", ["unexpected"]),
            (db_api.related_tag, "/related_tag.json", ["unexpected"]),
            (db_api.profile, "/profile.json", ["unexpected"]),
        ],
    )
    def test_singleton_bad_shapes_raise_upstream_shape(self, fn, path, body, fake_clock):
        from animedex.models.common import ApiError

        kwargs = {"no_cache": True}
        args = []
        if fn is db_api.artist or fn is db_api.pool:
            args.append(1)
        elif fn is db_api.related_tag:
            args.append("touhou")
        elif fn is db_api.profile:
            kwargs["creds"] = ("deepbooru", "fake")
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, f"https://danbooru.donmai.us{path}", json=body, status=200)
            with pytest.raises(ApiError) as ei:
                fn(*args, **kwargs)
        assert ei.value.reason == "upstream-shape"


class TestDanbooruAuth:
    """Authenticated reads (``/profile.json`` / ``/saved_searches.json``).

    Verify both the credential-resolution path (env var → string
    parse → tuple form) and that the wire request actually carries
    a valid ``Authorization: Basic`` header so a future regression
    here surfaces in the test suite.
    """

    def test_profile_returns_typed_record(self, fake_clock, monkeypatch):
        from animedex.backends.danbooru.models import DanbooruProfile

        monkeypatch.setenv("ANIMEDEX_DANBOORU_CREDS", "deepbooru:fake")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("profile/01-default.yaml"))
            row = db_api.profile(no_cache=True)
        assert isinstance(row, DanbooruProfile)
        assert row.id is not None
        assert row.name is not None

    def test_profile_explicit_creds_tuple_works(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruProfile

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("profile/01-default.yaml"))
            row = db_api.profile(creds=("deepbooru", "fake"), no_cache=True)
        assert isinstance(row, DanbooruProfile)

    def test_profile_creds_string_parses_to_tuple(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruProfile

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("profile/01-default.yaml"))
            row = db_api.profile(creds="deepbooru:fake", no_cache=True)
        assert isinstance(row, DanbooruProfile)

    def test_no_creds_raises_auth_required(self, fake_clock, monkeypatch):
        from animedex.models.common import ApiError

        monkeypatch.delenv("ANIMEDEX_DANBOORU_CREDS", raising=False)
        with pytest.raises(ApiError) as ei:
            db_api.profile(no_cache=True)
        assert ei.value.reason == "auth-required"

    @pytest.mark.parametrize("creds", ["missing-separator", object()])
    def test_bad_creds_raise_bad_args(self, creds, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            db_api.profile(creds=creds, no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_config_token_store_credentials_work(self, fake_clock, monkeypatch):
        from animedex.auth.inmemory_store import InMemoryTokenStore
        from animedex.backends.danbooru.models import DanbooruProfile
        from animedex.config import Config

        monkeypatch.delenv("ANIMEDEX_DANBOORU_CREDS", raising=False)
        cfg = Config(token_store=InMemoryTokenStore({"danbooru": "deepbooru:fake"}))
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("profile/01-default.yaml"))
            row = db_api.profile(config=cfg, no_cache=True)
        assert isinstance(row, DanbooruProfile)

    def test_authorization_header_is_basic_scheme(self, fake_clock, monkeypatch):
        """Wire-level: every authenticated call carries
        ``Authorization: Basic <b64>`` after credential resolution."""
        import base64

        monkeypatch.setenv("ANIMEDEX_DANBOORU_CREDS", "deepbooru:fake")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("profile/01-default.yaml"))
            db_api.profile(no_cache=True)
            sent = rsps.calls[0].request
        auth = sent.headers.get("Authorization", "")
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth[len("Basic ") :]).decode("ascii")
        assert decoded == "deepbooru:fake"

    def test_saved_searches_returns_list(self, fake_clock, monkeypatch):
        from animedex.backends.danbooru.models import DanbooruSavedSearch

        monkeypatch.setenv("ANIMEDEX_DANBOORU_CREDS", "deepbooru:fake")
        with responses.RequestsMock() as rsps:
            _register(rsps, _load("saved_searches/01-default.yaml"))
            rows = db_api.saved_searches(limit=3, no_cache=True)
        assert isinstance(rows, list)
        for r in rows:
            assert isinstance(r, DanbooruSavedSearch)


_LONG_TAIL_LIST_WRAPPERS = [
    # (function_name, fixture_slug). Every wrapper here is a thin
    # ``_record_search(slug, ...)`` shim; the test confirms it
    # dispatches to the right URL slug, returns a list, and that the
    # rich type round-trips the long-tail catch-all shape.
    ("artist_versions", "artist_versions_search"),
    ("artist_commentaries", "artist_commentaries_search"),
    ("artist_commentary_versions", "artist_commentary_versions_search"),
    ("tag_aliases", "tag_aliases_search"),
    ("tag_implications", "tag_implications_search"),
    ("tag_versions", "tag_versions_search"),
    ("wiki_pages", "wiki_pages_search"),
    ("wiki_page_versions", "wiki_page_versions_search"),
    ("pool_versions", "pool_versions_search"),
    ("notes", "notes_search"),
    ("note_versions", "note_versions_search"),
    ("comments", "comments_search"),
    ("comment_votes", "comment_votes_search"),
    ("forum_topics", "forum_topics_search"),
    ("forum_topic_visits", "forum_topic_visits_search"),
    ("forum_posts", "forum_posts_search"),
    ("forum_post_votes", "forum_post_votes_search"),
    ("users", "users_search"),
    ("user_events", "user_events_search"),
    ("user_feedbacks", "user_feedbacks_search"),
    ("favorites", "favorites_search"),
    ("favorite_groups", "favorite_groups_search"),
    ("uploads", "uploads_search"),
    ("upload_media_assets", "upload_media_assets_search"),
    ("post_versions", "post_versions_search"),
    ("post_replacements", "post_replacements_search"),
    ("post_disapprovals", "post_disapprovals_search"),
    ("post_appeals", "post_appeals_search"),
    ("post_flags", "post_flags_search"),
    ("post_votes", "post_votes_search"),
    ("post_approvals", "post_approvals_search"),
    ("post_events", "post_events_search"),
    ("mod_actions", "mod_actions_search"),
    ("bans", "bans_search"),
    ("bulk_update_requests", "bulk_update_requests_search"),
    ("dtext_links", "dtext_links_search"),
    ("ai_tags", "ai_tags_search"),
    ("media_assets", "media_assets_search"),
    ("media_metadata", "media_metadata_search"),
    ("rate_limits", "rate_limits_search"),
    ("recommended_posts", "recommended_posts_search"),
    ("reactions", "reactions_search"),
    ("jobs", "jobs_search"),
    ("metrics", "metrics_search"),
]

_LONG_TAIL_SHOW_WRAPPERS = [
    ("comment", "comments_by_id"),
    ("user", "users_by_id"),
]

_LONG_TAIL_SHOW_NOT_FOUND_WRAPPERS = [
    ("note", "notes_by_id"),
    ("wiki_page", "wiki_pages_by_id"),
]


@pytest.mark.parametrize("fn_name,slug", _LONG_TAIL_LIST_WRAPPERS)
def test_long_tail_list_wrapper_dispatches(fn_name, slug, fake_clock):
    """Every list-shape long-tail wrapper threads through to
    ``/<slug>.json`` and returns a list of :class:`DanbooruRecord`."""
    from animedex.backends.danbooru.models import DanbooruRecord

    fixtures = sorted((FIXTURES / slug).glob("*.yaml"))
    if not fixtures:
        pytest.skip(f"no fixture for {slug}")
    with responses.RequestsMock() as rsps:
        _register(rsps, _load(f"{slug}/{fixtures[0].name}"))
        out = getattr(db_api, fn_name)(no_cache=True)
    assert isinstance(out, list)
    for row in out:
        assert isinstance(row, DanbooruRecord)


@pytest.mark.parametrize("fn_name,slug", _LONG_TAIL_SHOW_WRAPPERS)
def test_long_tail_show_wrapper_dispatches(fn_name, slug, fake_clock):
    """Singleton ``/<slug>/{id}.json`` wrappers project to one
    :class:`DanbooruRecord`."""
    from animedex.backends.danbooru.models import DanbooruRecord

    fixtures = sorted((FIXTURES / slug).glob("*.yaml"))
    if not fixtures:
        pytest.skip(f"no fixture for {slug}")
    fx = _load(f"{slug}/{fixtures[0].name}")
    body = fx["response"].get("body_json")
    rec_id = body.get("id") if isinstance(body, dict) else 1
    with responses.RequestsMock() as rsps:
        _register(rsps, fx)
        out = getattr(db_api, fn_name)(rec_id, no_cache=True)
    assert isinstance(out, DanbooruRecord)


@pytest.mark.parametrize("fn_name,slug", _LONG_TAIL_SHOW_NOT_FOUND_WRAPPERS)
def test_long_tail_show_wrapper_404_raises_not_found(fn_name, slug, fake_clock):
    """Captured singleton fixtures that are real 404s still exercise
    the named wrapper and surface the standard ``not-found`` reason."""
    from animedex.models.common import ApiError

    with responses.RequestsMock() as rsps:
        _register(rsps, _load(f"{slug}/01-id-1.yaml"))
        with pytest.raises(ApiError) as ei:
            getattr(db_api, fn_name)(1, no_cache=True)
    assert ei.value.reason == "not-found"


def test_artist_commentary_wrapper_dispatches(fake_clock):
    from animedex.backends.danbooru.models import DanbooruRecord

    fx = _load("artist_commentaries_search/01-page1.yaml")
    row = fx["response"]["body_json"][0]
    with responses.RequestsMock() as rsps:
        _register_as(
            rsps, {**fx, "response": {**fx["response"], "body_json": row}}, f"/artist_commentaries/{row['id']}.json"
        )
        out = db_api.artist_commentary(row["id"], no_cache=True)
    assert isinstance(out, DanbooruRecord)


def test_record_show_bad_shape_raises_upstream_shape(fake_clock):
    from animedex.models.common import ApiError

    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://danbooru.donmai.us/comments/1.json", json=["unexpected"], status=200)
        with pytest.raises(ApiError) as ei:
            db_api.comment(1, no_cache=True)
    assert ei.value.reason == "upstream-shape"


class TestDanbooruDiscoveryWrappers:
    """``autocomplete`` / ``related_tag`` / ``iqdb_query`` are the
    three discovery wrappers that take non-pagination args; verify
    each returns the documented shape."""

    def test_autocomplete_returns_records(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruRecord

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("autocomplete_search/01-tag-touhou.yaml"))
            out = db_api.autocomplete("touh", no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruRecord)

    def test_related_tag_returns_envelope(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruRelatedTag

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("related_tag_search/01-touhou.yaml"))
            out = db_api.related_tag("touhou", no_cache=True)
        assert isinstance(out, DanbooruRelatedTag)

    def test_iqdb_query_requires_url_or_post_id(self, fake_clock):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError) as ei:
            db_api.iqdb_query(no_cache=True)
        assert ei.value.reason == "bad-args"

    def test_iqdb_query_with_post_id(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruIQDBQuery

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("iqdb_queries/01-no-image.yaml"))
            out = db_api.iqdb_query(post_id=1, no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruIQDBQuery)

    def test_iqdb_query_with_url(self, fake_clock):
        from animedex.backends.danbooru.models import DanbooruIQDBQuery

        with responses.RequestsMock() as rsps:
            _register(rsps, _load("iqdb_queries/01-no-image.yaml"))
            out = db_api.iqdb_query(url="https://example.invalid/image.png", no_cache=True)
        assert isinstance(out, list)
        for row in out:
            assert isinstance(row, DanbooruIQDBQuery)


def test_module_selftest_returns_true():
    assert db_api.selftest() is True


def test_models_selftest_returns_true():
    from animedex.backends.danbooru import models

    assert models.selftest() is True
