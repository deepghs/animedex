"""Lossless round-trip tests for every backend rich dataclass.

Per AGENTS.md §9bis + §13: backend-specific rich types
(``AnilistAnime``, ``JikanAnime``, ``RawTraceHit``, ...) must be
information-lossless. Feeding the upstream payload into
``Model.model_validate(payload)`` and dumping with
``model_dump(by_alias=True, mode='json')`` must produce a result
whose key set is a *superset* of the upstream's.

Each test parametrises over every fixture in the relevant
``test/fixtures/`` slug and walks the upstream key tree against the
dumped key tree. A missing key fails the test with a precise
``LOST: <path>`` diagnostic.

This is the test suite that pins the "rich = lossless" contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Set

import pytest
import yaml

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "test" / "fixtures"


def _src() -> SourceTag:
    return SourceTag(backend="x", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


def _key_tree(obj: Any, prefix: str = "") -> Set[str]:
    """Recursive key set, encoding lists as ``[]`` so equivalent
    arrays at the same path collapse into one entry."""
    out: Set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{prefix}.{k}" if prefix else k
            out.add(kp)
            out |= _key_tree(v, kp)
    elif isinstance(obj, list) and obj:
        # Walk every element so divergent shapes between rows don't
        # silently mask field loss.
        for item in obj:
            out |= _key_tree(item, prefix + "[]")
    return out


def _load(rel: str) -> dict:
    return yaml.safe_load((FIXTURES / rel).read_text(encoding="utf-8"))


def _round_trip_keys(model_cls, raw: dict) -> Set[str]:
    """Validate ``raw`` through ``model_cls``, dump it back, return
    the dumped key tree."""
    obj = model_cls.model_validate({**raw, "source_tag": _src()})
    dumped = obj.model_dump(mode="json", by_alias=True, exclude={"source_tag"})
    return _key_tree(dumped)


def _assert_lossless(model_cls, raw: dict, label: str):
    upstream = _key_tree(raw)
    after = _round_trip_keys(model_cls, raw)
    lost = upstream - after
    assert not lost, (
        f"{label}: rich model dropped {len(lost)} key(s). "
        f"Backend rich models must be lossless per AGENTS §13. Lost paths: {sorted(lost)[:20]}"
    )


# ---------- AniList core ----------


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "media").glob("*.yaml")))
def test_anilist_anime_lossless(path):
    from animedex.backends.anilist.models import AnilistAnime

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Media"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistAnime, raw, f"AnilistAnime/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "character").glob("*.yaml")))
def test_anilist_character_lossless(path):
    from animedex.backends.anilist.models import AnilistCharacter

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Character"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistCharacter, raw, f"AnilistCharacter/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "staff").glob("*.yaml")))
def test_anilist_staff_lossless(path):
    from animedex.backends.anilist.models import AnilistStaff

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Staff"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistStaff, raw, f"AnilistStaff/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "studio").glob("*.yaml")))
def test_anilist_studio_lossless(path):
    from animedex.backends.anilist.models import AnilistStudio

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Studio"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistStudio, raw, f"AnilistStudio/{path.name}")


# ---------- Jikan core ----------


@pytest.mark.parametrize("path", sorted((FIXTURES / "jikan" / "anime_full").glob("*.yaml")))
def test_jikan_anime_lossless(path):
    from animedex.backends.jikan.models import JikanAnime

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
    if raw.get("status") in (404, 500):
        pytest.skip("error-response fixture")
    if "data" not in raw:
        pytest.skip("not a /full payload")
    _assert_lossless(JikanAnime, raw["data"], f"JikanAnime/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "jikan" / "manga_full").glob("*.yaml")))
def test_jikan_manga_lossless(path):
    from animedex.backends.jikan.models import JikanManga

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
    if "data" not in raw:
        pytest.skip("not a /full payload")
    _assert_lossless(JikanManga, raw["data"], f"JikanManga/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "jikan" / "characters_full").glob("*.yaml")))
def test_jikan_character_lossless(path):
    from animedex.backends.jikan.models import JikanCharacter

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
    if "data" not in raw:
        pytest.skip("not a /full payload")
    _assert_lossless(JikanCharacter, raw["data"], f"JikanCharacter/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "jikan" / "people_full").glob("*.yaml")))
def test_jikan_person_lossless(path):
    from animedex.backends.jikan.models import JikanPerson

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
    if "data" not in raw:
        pytest.skip("not a /full payload")
    _assert_lossless(JikanPerson, raw["data"], f"JikanPerson/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "jikan" / "producers_full").glob("*.yaml")))
def test_jikan_producer_lossless(path):
    from animedex.backends.jikan.models import JikanProducer

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
    if "data" not in raw:
        pytest.skip("not a /full payload")
    _assert_lossless(JikanProducer, raw["data"], f"JikanProducer/{path.name}")


# ---------- Trace ----------


class TestTraceLossless:
    @pytest.mark.parametrize("path", sorted((FIXTURES / "trace" / "search").glob("*.yaml")))
    def test_trace_hit_lossless(self, path):
        from animedex.backends.trace.models import RawTraceHit

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("result"):
            pytest.skip("empty search fixture")
        for i, row in enumerate(body["result"]):
            _assert_lossless(RawTraceHit, row, f"RawTraceHit/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "trace" / "me").glob("*.yaml")))
    def test_trace_quota_lossless(self, path):
        from animedex.backends.trace.models import RawTraceQuota

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body:
            pytest.skip("empty fixture")
        # The rich shape is fully lossless, ``id`` included. The
        # upstream's ``id`` is the caller's egress IP — surfacing it on
        # the rich model is correct (it's the caller's own datum, not
        # something to filter on their behalf, AGENTS §0). The
        # fixture-capture pipeline rewrites public IPv4 addresses to
        # the RFC-5737 documentation address, so the repo's fixtures
        # never carry a real contributor IP. The common projection
        # :class:`TraceQuota` does not include ``id``, so callers who
        # don't want the IP reach for it.
        _assert_lossless(RawTraceQuota, body, f"RawTraceQuota/{path.name}")
        # The common projection deliberately does NOT have an ``id``
        # field — pin that here so the asymmetry is enforced.
        from animedex.models.trace import TraceQuota

        assert "id" not in TraceQuota.model_fields, (
            "TraceQuota.id appeared on the common projection — the rich shape carries the IP, "
            "the common shape does not. See AGENTS §13."
        )


# ---------- Kitsu ----------


class TestKitsuLossless:
    """Kitsu's JSON:API resource shape is ``{id, type, attributes,
    relationships, links}``. The rich types model the ``attributes``
    block as a typed sub-class with ``extra='allow'`` so any field
    upstream adds round-trips through ``model_dump`` even if not
    declared."""

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "anime_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_anime_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuAnime

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or "data" not in body or body["data"] is None:
            pytest.skip("empty / not-found fixture")
        _assert_lossless(KitsuAnime, body["data"], f"KitsuAnime/{path.name}")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "anime_search").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "trending_anime").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_anime_listing_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuAnime

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuAnime, row, f"KitsuAnime/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "trending_manga").glob("*.yaml")))
    def test_kitsu_manga_trending_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuManga

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuManga, row, f"KitsuManga/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "characters").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "characters_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_character_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuCharacter

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuCharacter, row, f"KitsuCharacter/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "people").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "people_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_person_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuPerson

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuPerson, row, f"KitsuPerson/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "producers").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "producers_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_producer_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuProducer

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuProducer, row, f"KitsuProducer/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "genres").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "genres_by_id").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_genres").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "manga_genres").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_genre_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuGenre

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuGenre, row, f"KitsuGenre/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "streamers").glob("*.yaml")))
    def test_kitsu_streamer_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuStreamer

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuStreamer, row, f"KitsuStreamer/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "franchises").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "franchises_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_franchise_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuFranchise

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuFranchise, row, f"KitsuFranchise/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "users_by_id").glob("*.yaml")))
    def test_kitsu_user_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuUser

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuUser, row, f"KitsuUser/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "anime_characters").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_staff").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_episodes").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_reviews").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_relations").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "anime_productions").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "manga_characters").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "manga_staff").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "manga_chapters").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "people_voices").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "people_castings").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "users_library_entries").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "users_stats").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_related_resource_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuRelatedResource

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuRelatedResource, row, f"KitsuRelatedResource/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "kitsu" / "manga_by_id").glob("*.yaml"),
                *(FIXTURES / "kitsu" / "manga_search").glob("*.yaml"),
            ]
        ),
    )
    def test_kitsu_manga_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuManga

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or "data" not in body or body["data"] is None:
            pytest.skip("empty / not-found fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(KitsuManga, row, f"KitsuManga/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "anime_mappings").glob("*.yaml")))
    def test_kitsu_mapping_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuMapping

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuMapping, row, f"KitsuMapping/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "anime_streaming_links").glob("*.yaml")))
    def test_kitsu_streaming_link_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuStreamingLink

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuStreamingLink, row, f"KitsuStreamingLink/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "kitsu" / "categories").glob("*.yaml")))
    def test_kitsu_category_lossless(self, path):
        from animedex.backends.kitsu.models import KitsuCategory

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(KitsuCategory, row, f"KitsuCategory/{path.name}[{i}]")


# ---------- MangaDex ----------


class TestMangaDexLossless:
    """MangaDex's resource shape is JSON:API-flavoured —
    ``{id, type, attributes, relationships}``. Listings come in a
    ``{result, response, data: [...], limit, offset, total}``
    envelope; the rich types model the inner ``data`` resource.

    Some PR #4 fixtures captured 4xx/5xx from upstream weather
    (the ``manga_by_id`` slug has a couple of error responses
    where ``data`` is missing); ``_skip_error_envelopes`` filters
    those so the lossless walk only audits success payloads.
    """

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "mangadex" / "manga_by_id").glob("*.yaml"),
            ]
        ),
    )
    def test_mangadex_manga_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexManga

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or "data" not in body or body["data"] is None:
            pytest.skip("error / not-found fixture")
        _assert_lossless(MangaDexManga, body["data"], f"MangaDexManga/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "manga_search").glob("*.yaml")))
    def test_mangadex_manga_search_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexManga

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(MangaDexManga, row, f"MangaDexManga/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "manga_feed").glob("*.yaml")))
    def test_mangadex_chapter_feed_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexChapter

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(MangaDexChapter, row, f"MangaDexChapter/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "chapter_by_id").glob("*.yaml")))
    def test_mangadex_chapter_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexChapter

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or "data" not in body or body["data"] is None:
            pytest.skip("error / not-found fixture")
        _assert_lossless(MangaDexChapter, body["data"], f"MangaDexChapter/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "cover_by_id").glob("*.yaml")))
    def test_mangadex_cover_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexCover

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or "data" not in body or body["data"] is None:
            pytest.skip("error / not-found fixture")
        _assert_lossless(MangaDexCover, body["data"], f"MangaDexCover/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "chapter_search").glob("*.yaml")))
    def test_mangadex_chapter_search_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexChapter

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(MangaDexChapter, row, f"MangaDexChapter/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "mangadex" / "cover_search").glob("*.yaml")))
    def test_mangadex_cover_search_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexCover

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["data"]):
            _assert_lossless(MangaDexCover, row, f"MangaDexCover/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "mangadex" / "manga_random").glob("*.yaml"),
            ]
        ),
    )
    def test_mangadex_manga_random_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexManga

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        d = body["data"] if isinstance(body["data"], dict) else (body["data"][0] if body["data"] else None)
        if d is None:
            pytest.skip("no data")
        _assert_lossless(MangaDexManga, d, f"MangaDexManga/{path.name}")

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "mangadex" / "author_by_id").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "author_search").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "group_by_id").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "group_search").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "manga_recommendation").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "manga_tag").glob("*.yaml"),
                *(FIXTURES / "mangadex" / "report_reasons_category").glob("*.yaml"),
            ]
        ),
    )
    def test_mangadex_resource_lossless(self, path):
        from animedex.backends.mangadex.models import MangaDexResource

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or body.get("result") == "error" or not body.get("data"):
            pytest.skip("empty fixture")
        rows = body["data"] if isinstance(body["data"], list) else [body["data"]]
        for i, row in enumerate(rows):
            _assert_lossless(MangaDexResource, row, f"MangaDexResource/{path.name}[{i}]")


# ---------- Danbooru ----------


class TestDanbooruLossless:
    """Danbooru's REST surface returns flat JSON objects directly;
    the rich types map fields one-for-one with extra='allow' so any
    upstream addition round-trips."""

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "danbooru" / "posts_search").glob("*.yaml"),
            ]
        ),
    )
    def test_danbooru_post_search_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruPost

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body:
            pytest.skip("empty fixture")
        if not isinstance(body, list):
            pytest.skip("error fixture")
        for i, row in enumerate(body):
            _assert_lossless(DanbooruPost, row, f"DanbooruPost/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "posts_by_id").glob("*.yaml")))
    def test_danbooru_post_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruPost

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "id" not in body:
            pytest.skip("error / non-dict fixture")
        _assert_lossless(DanbooruPost, body, f"DanbooruPost/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "artists_search").glob("*.yaml")))
    def test_danbooru_artist_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruArtist

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, list):
            pytest.skip("empty fixture")
        for i, row in enumerate(body):
            _assert_lossless(DanbooruArtist, row, f"DanbooruArtist/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "tags_search").glob("*.yaml")))
    def test_danbooru_tag_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruTag

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, list):
            pytest.skip("empty fixture")
        for i, row in enumerate(body):
            _assert_lossless(DanbooruTag, row, f"DanbooruTag/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "pools_by_id").glob("*.yaml")))
    def test_danbooru_pool_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruPool

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "id" not in body:
            pytest.skip("error / non-dict fixture")
        _assert_lossless(DanbooruPool, body, f"DanbooruPool/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "counts").glob("*.yaml")))
    def test_danbooru_count_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruCount

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "counts" not in body:
            pytest.skip("error fixture")
        _assert_lossless(DanbooruCount, body, f"DanbooruCount/{path.name}")

    # ---------- DanbooruRecord catch-all (paginated long-tail feeds) ----------
    #
    # Every long-tail Danbooru endpoint (versions / votes / events / forum /
    # commentary / moderation / operational) returns the same uniform shape:
    # a flat ``[{id, ...}, ...]`` (or a single dict for ``/<slug>/{id}.json``).
    # The ``DanbooruRecord`` model is the catch-all that exists to round-trip
    # every such payload losslessly without spelling out per-endpoint typed
    # subclasses (which would multiply the model count without much downstream
    # benefit; ``extra='allow'`` covers the unmodelled keys).

    _DANBOORU_RECORD_LIST_SLUGS = [
        "ai_tags_search",
        "artist_commentaries_search",
        "artist_commentary_versions_search",
        "artist_versions_search",
        "autocomplete_search",
        "bans_search",
        "bulk_update_requests_search",
        "comment_votes_search",
        "comments_search",
        "dtext_links_search",
        "favorite_groups_search",
        "favorites_search",
        "forum_post_votes_search",
        "forum_posts_search",
        "forum_topic_visits_search",
        "forum_topics_search",
        "jobs_search",
        "media_assets_search",
        "media_metadata_search",
        "metrics_search",
        "mod_actions_search",
        "note_versions_search",
        "notes_search",
        "pool_versions_search",
        "post_appeals_search",
        "post_approvals_search",
        "post_disapprovals_search",
        "post_events_search",
        "post_flags_search",
        "post_replacements_search",
        "post_versions_search",
        "post_votes_search",
        "rate_limits_search",
        "reactions_search",
        "recommended_posts_search",
        "tag_aliases_search",
        "tag_implications_search",
        "tag_versions_search",
        "upload_media_assets_search",
        "uploads_search",
        "user_events_search",
        "user_feedbacks_search",
        "users_search",
        "wiki_page_versions_search",
        "wiki_pages_search",
    ]

    _DANBOORU_RECORD_BY_ID_SLUGS = [
        "comments_by_id",
        "notes_by_id",
        "users_by_id",
        "wiki_pages_by_id",
    ]

    @pytest.mark.parametrize(
        "path",
        sorted(p for slug in _DANBOORU_RECORD_LIST_SLUGS for p in (FIXTURES / "danbooru" / slug).glob("*.yaml")),
        ids=lambda p: f"{p.parent.name}/{p.stem}",
    )
    def test_danbooru_record_list_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruRecord

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, list):
            pytest.skip("empty / error / non-list fixture")
        for i, row in enumerate(body):
            if not isinstance(row, dict):
                continue
            _assert_lossless(DanbooruRecord, row, f"DanbooruRecord/{path.parent.name}/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(p for slug in _DANBOORU_RECORD_BY_ID_SLUGS for p in (FIXTURES / "danbooru" / slug).glob("*.yaml")),
        ids=lambda p: f"{p.parent.name}/{p.stem}",
    )
    def test_danbooru_record_by_id_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruRecord

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict):
            pytest.skip("error / non-dict fixture")
        _assert_lossless(DanbooruRecord, body, f"DanbooruRecord/{path.parent.name}/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "related_tag_search").glob("*.yaml")))
    def test_danbooru_related_tag_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruRelatedTag

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict):
            pytest.skip("error / non-dict fixture")
        _assert_lossless(DanbooruRelatedTag, body, f"DanbooruRelatedTag/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "danbooru" / "iqdb_queries").glob("*.yaml")))
    def test_danbooru_iqdb_query_lossless(self, path):
        from animedex.backends.danbooru.models import DanbooruIQDBQuery

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body:
            pytest.skip("empty fixture")
        if not isinstance(body, list):
            pytest.skip("error fixture")
        for i, row in enumerate(body):
            if not isinstance(row, dict):
                continue
            _assert_lossless(DanbooruIQDBQuery, row, f"DanbooruIQDBQuery/{path.name}[{i}]")


# ---------- Waifu.im ----------


class TestWaifuLossless:
    """Waifu.im wraps every listing in a paginated envelope; the
    rich types model the inner ``items`` row shape."""

    @pytest.mark.parametrize("path", sorted((FIXTURES / "waifu" / "tags").glob("*.yaml")))
    def test_waifu_tag_lossless(self, path):
        from animedex.backends.waifu.models import WaifuTag

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("items"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["items"]):
            _assert_lossless(WaifuTag, row, f"WaifuTag/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "waifu" / "artists").glob("*.yaml")))
    def test_waifu_artist_lossless(self, path):
        from animedex.backends.waifu.models import WaifuArtist

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("items"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["items"]):
            _assert_lossless(WaifuArtist, row, f"WaifuArtist/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "waifu" / "images").glob("*.yaml")))
    def test_waifu_image_lossless(self, path):
        from animedex.backends.waifu.models import WaifuImage

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("items"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["items"]):
            _assert_lossless(WaifuImage, row, f"WaifuImage/{path.name}[{i}]")

    @pytest.mark.parametrize(
        "path",
        sorted(
            list((FIXTURES / "waifu" / "tags_by_id").glob("*.yaml"))
            + list((FIXTURES / "waifu" / "tags_by_slug").glob("*.yaml"))
        ),
        ids=lambda p: f"{p.parent.name}/{p.stem}",
    )
    def test_waifu_tag_singleton_lossless(self, path):
        from animedex.backends.waifu.models import WaifuTag

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "id" not in body:
            pytest.skip("error / non-dict fixture")
        _assert_lossless(WaifuTag, body, f"WaifuTag/{path.parent.name}/{path.name}")

    @pytest.mark.parametrize(
        "path",
        sorted(
            list((FIXTURES / "waifu" / "artists_by_id").glob("*.yaml"))
            + list((FIXTURES / "waifu" / "artists_by_name").glob("*.yaml"))
        ),
        ids=lambda p: f"{p.parent.name}/{p.stem}",
    )
    def test_waifu_artist_singleton_lossless(self, path):
        from animedex.backends.waifu.models import WaifuArtist

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "id" not in body:
            pytest.skip("error / non-dict fixture")
        _assert_lossless(WaifuArtist, body, f"WaifuArtist/{path.parent.name}/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "waifu" / "images_by_id").glob("*.yaml")))
    def test_waifu_image_singleton_lossless(self, path):
        from animedex.backends.waifu.models import WaifuImage

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict) or "id" not in body:
            pytest.skip("error / non-dict fixture")
        _assert_lossless(WaifuImage, body, f"WaifuImage/{path.name}")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "waifu" / "stats_public").glob("*.yaml")))
    def test_waifu_stats_lossless(self, path):
        from animedex.backends.waifu.models import WaifuStats

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not isinstance(body, dict):
            pytest.skip("error / non-dict fixture")
        _assert_lossless(WaifuStats, body, f"WaifuStats/{path.name}")


# ---------- nekos.best ----------


class TestNekosLossless:
    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(FIXTURES / "nekos" / "husbando").glob("*.yaml"),
                *(FIXTURES / "nekos" / "neko").glob("*.yaml"),
                *(FIXTURES / "nekos" / "waifu").glob("*.yaml"),
                *(FIXTURES / "nekos" / "baka").glob("*.yaml"),
                *(FIXTURES / "nekos" / "search").glob("*.yaml"),
            ]
        ),
    )
    def test_nekos_image_lossless(self, path):
        from animedex.backends.nekos.models import NekosImage

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body or not body.get("results"):
            pytest.skip("empty fixture")
        for i, row in enumerate(body["results"]):
            _assert_lossless(NekosImage, row, f"NekosImage/{path.name}[{i}]")

    @pytest.mark.parametrize("path", sorted((FIXTURES / "nekos" / "endpoints").glob("*.yaml")))
    def test_nekos_category_format_lossless(self, path):
        from animedex.backends.nekos.models import NekosCategoryFormat

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]
        # /endpoints emits a flat dict-of-categories; each VALUE is the
        # per-record shape that NekosCategoryFormat models. Walk every
        # category so a future drift in any single entry surfaces.
        for cat_name, cat_format in body.items():
            _assert_lossless(NekosCategoryFormat, cat_format, f"NekosCategoryFormat/{path.name}[{cat_name}]")


# ---------- Smoke: every rich class has BackendRichModel discipline ----------


class TestBackendRichDiscipline:
    """Every class in animedex.backends.<x>.models that ends in a
    public name (not _ prefixed and not the helper sub-types) must
    inherit from :class:`BackendRichModel`."""

    def test_anilist_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.anilist import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"AniList classes outside BackendRichModel: {not_rich}"

    def test_jikan_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.jikan import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Jikan classes outside BackendRichModel: {not_rich}"

    def test_trace_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.trace import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Trace classes outside BackendRichModel: {not_rich}"

    def test_nekos_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.nekos import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Nekos classes outside BackendRichModel: {not_rich}"

    def test_kitsu_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.kitsu import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Kitsu classes outside BackendRichModel: {not_rich}"

    def test_mangadex_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.mangadex import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"MangaDex classes outside BackendRichModel: {not_rich}"

    def test_danbooru_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.danbooru import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Danbooru classes outside BackendRichModel: {not_rich}"

    def test_waifu_module_uses_backend_rich_base(self):
        from animedex.models.common import BackendRichModel
        from animedex.backends.waifu import models as m

        rich_classes = [c for c in vars(m).values() if isinstance(c, type) and c.__module__ == m.__name__]
        not_rich = [c.__name__ for c in rich_classes if not issubclass(c, BackendRichModel)]
        assert not not_rich, f"Waifu classes outside BackendRichModel: {not_rich}"
