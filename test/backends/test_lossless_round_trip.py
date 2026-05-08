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


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "phase2_media").glob("*.yaml")))
def test_anilist_anime_lossless(path):
    from animedex.backends.anilist.models import AnilistAnime

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Media"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistAnime, raw, f"AnilistAnime/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "phase2_character").glob("*.yaml")))
def test_anilist_character_lossless(path):
    from animedex.backends.anilist.models import AnilistCharacter

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Character"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistCharacter, raw, f"AnilistCharacter/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "phase2_staff").glob("*.yaml")))
def test_anilist_staff_lossless(path):
    from animedex.backends.anilist.models import AnilistStaff

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["response"]["body_json"]["data"]["Staff"]
    if raw is None:
        pytest.skip("not-found fixture")
    _assert_lossless(AnilistStaff, raw, f"AnilistStaff/{path.name}")


@pytest.mark.parametrize("path", sorted((FIXTURES / "anilist" / "phase2_studio").glob("*.yaml")))
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
    def test_trace_quota_lossless_minus_id(self, path):
        from animedex.backends.trace.models import RawTraceQuota

        body = yaml.safe_load(path.read_text(encoding="utf-8"))["response"].get("body_json")
        if not body:
            pytest.skip("empty fixture")
        # ``id`` (caller IP) is deliberately dropped.
        upstream = _key_tree(body) - {"id"}
        obj = RawTraceQuota.model_validate({**body, "source_tag": _src()})
        dumped = obj.model_dump(mode="json", by_alias=True, exclude={"source_tag"})
        after = _key_tree(dumped)
        # ``id`` must NOT survive
        assert "id" not in after, "RawTraceQuota leaked the caller IP back through dump"
        # everything else must be preserved
        lost = upstream - after
        assert not lost, f"RawTraceQuota dropped non-id keys: {sorted(lost)}"


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
