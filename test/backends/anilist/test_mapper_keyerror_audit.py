"""Reviewer review B4 (PR #6) — mapper KeyError audit.

The Phase-2 mapper had ``r[\"timeUntilAiring\"]`` that crashed with
``KeyError`` for already-aired schedule entries. The same pattern of
indexing without a default repeats throughout :mod:`animedex.backends.anilist._mapper`.

Contract: when an upstream row is *missing a required field*, the
mapper must raise a typed :class:`ApiError` with
``reason='upstream-shape'``, not a bare :class:`KeyError`. The typed
error is what the dispatcher / CLI / library callers know how to
catch; a ``KeyError`` is a leaked internal failure mode that points at
the wrong line of code.

These parametrised tests feed every list-mapper an upstream-shaped
payload that omits the ``id`` field on the row. The pre-fix mappers
crash with ``KeyError: 'id'``; the post-fix mappers raise
``ApiError(reason='upstream-shape')``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Tuple

import pytest

from animedex.models.common import ApiError, SourceTag


pytestmark = pytest.mark.unittest


def _src() -> SourceTag:
    return SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


# ---------- list-mapper cases ----------
#
# Each entry: (mapper_name, payload_template_for_a_row_missing_id,
# top-level-data-key-path)
#
# The payload structure is what AniList's GraphQL API returns; we
# provide one row that *should* validate cleanly but for the missing
# ``id`` field. The pre-fix mappers crash; the post-fix mappers must
# raise upstream-shape ApiError.

LIST_MAPPER_CASES: List[Tuple[str, Dict[str, Any]]] = [
    (
        "map_airing_schedule",
        {"data": {"Page": {"airingSchedules": [{"airingAt": 0, "episode": 1, "timeUntilAiring": 0}]}}},
    ),
    (
        "map_review",
        {"data": {"Page": {"reviews": [{"summary": "x"}]}}},
    ),
    (
        "map_recommendation",
        {"data": {"Page": {"recommendations": [{"rating": 0}]}}},
    ),
    (
        "map_thread",
        {"data": {"Page": {"threads": [{"title": "x"}]}}},
    ),
    (
        "map_thread_comment",
        {"data": {"Page": {"threadComments": [{"comment": "x"}]}}},
    ),
    (
        "map_activity",
        {"data": {"Page": {"activities": [{"text": "x"}]}}},
    ),
    (
        "map_activity_reply",
        {"data": {"Page": {"activityReplies": [{"text": "x"}]}}},
    ),
    (
        "map_media_list_public",
        {"data": {"Page": {"mediaList": [{"status": "x"}]}}},
    ),
    (
        "map_notification",
        {"data": {"Page": {"notifications": [{"type": "AIRING"}]}}},
    ),
]


@pytest.mark.parametrize(
    "mapper_name,payload",
    LIST_MAPPER_CASES,
    ids=[c[0] for c in LIST_MAPPER_CASES],
)
def test_list_mapper_missing_id_raises_upstream_shape(mapper_name, payload):
    """A row missing its ``id`` field must produce
    ``ApiError(reason='upstream-shape')``, not a leaked KeyError."""
    from animedex.backends.anilist import _mapper as mp

    mapper: Callable = getattr(mp, mapper_name)
    with pytest.raises(ApiError) as exc_info:
        mapper(payload, _src())
    assert exc_info.value.reason == "upstream-shape", (
        f"{mapper_name}: expected reason='upstream-shape', got {exc_info.value.reason!r} "
        f"(message: {exc_info.value.message!r})"
    )


# ---------- airing_schedule's ORIGINAL bug regression ----------


def test_airing_schedule_missing_time_until_airing_does_not_crash():
    """Regression test for the canary bug. The ``not_yet_aired=True``
    fixture returned historical entries without ``timeUntilAiring``;
    the original mapper crashed with ``KeyError``. After the
    ``r.get(... 0)`` fix it shouldn't, but the broader audit is meant
    to keep this from regressing under refactor."""
    from animedex.backends.anilist import _mapper as mp

    payload = {
        "data": {
            "Page": {
                "airingSchedules": [
                    {"id": 1, "airingAt": 1234567890, "episode": 5},  # no timeUntilAiring
                ]
            }
        }
    }
    out = mp.map_airing_schedule(payload, _src())
    assert len(out) == 1
    assert out[0].id == 1
    assert out[0].timeUntilAiring == 0  # default


# ---------- happy-path regression ----------


def test_happy_path_still_works():
    """The audit changes must not break the happy-path mapping —
    a fully-populated row maps as before."""
    from animedex.backends.anilist import _mapper as mp

    payload = {
        "data": {"Page": {"reviews": [{"id": 314, "summary": "great", "score": 90, "rating": 12, "ratingAmount": 15}]}}
    }
    out = mp.map_review(payload, _src())
    assert len(out) == 1
    assert out[0].id == 314
    assert out[0].summary == "great"
