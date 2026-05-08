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
