"""
Tests for :mod:`animedex.models.common`.

These exercise the ground-floor types that every other model and every
backend builds on: :class:`~animedex.models.common.SourceTag` (the
provenance carrier behind the source-attribution contract from
``plans/03-cli-architecture-gh-flavored.md``), :class:`Pagination`,
:class:`RateLimit`, and :class:`ApiError`. The :class:`AnimedexModel`
base class is verified for the configuration knobs every later model
relies on (``populate_by_name``, ``extra='ignore'``, ``frozen=True``).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


class TestSourceTag:
    def test_minimal_construction(self):
        from animedex.models.common import SourceTag

        ts = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
        tag = SourceTag(backend="anilist", fetched_at=ts)

        assert tag.backend == "anilist"
        assert tag.fetched_at == ts
        assert tag.cached is False
        assert tag.rate_limited is False

    def test_full_construction(self):
        from animedex.models.common import SourceTag

        ts = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
        tag = SourceTag(backend="jikan", fetched_at=ts, cached=True, rate_limited=True)

        assert tag.cached is True
        assert tag.rate_limited is True

    def test_is_frozen(self):
        """Frozen models are required so cached payloads are safe to share."""
        from animedex.models.common import SourceTag

        tag = SourceTag(backend="kitsu", fetched_at=datetime.now(timezone.utc))
        with pytest.raises(Exception):
            tag.backend = "mangadex"

    def test_extra_fields_are_ignored(self):
        """Upstream may add fields without breaking our parsing."""
        from animedex.models.common import SourceTag

        tag = SourceTag.model_validate(
            {
                "backend": "anilist",
                "fetched_at": "2026-05-07T10:00:00+00:00",
                "future_field_we_do_not_know": 42,
            }
        )

        assert tag.backend == "anilist"
        assert not hasattr(tag, "future_field_we_do_not_know")

    def test_round_trip_json(self):
        """SourceTag must survive the cache layer's JSON serialisation."""
        from animedex.models.common import SourceTag

        ts = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
        original = SourceTag(backend="anilist", fetched_at=ts, cached=True)

        roundtripped = SourceTag.model_validate_json(original.model_dump_json())

        assert roundtripped == original


class TestPagination:
    def test_construction(self):
        from animedex.models.common import Pagination

        p = Pagination(page=1, per_page=20, total=200, has_next=True)
        assert p.page == 1
        assert p.per_page == 20
        assert p.total == 200
        assert p.has_next is True

    def test_defaults(self):
        """``total`` is optional because some upstreams don't expose it."""
        from animedex.models.common import Pagination

        p = Pagination(page=1, per_page=20, has_next=False)
        assert p.total is None


class TestRateLimit:
    def test_construction(self):
        from animedex.models.common import RateLimit

        rl = RateLimit(remaining=42, reset_at=datetime(2026, 5, 7, 10, 5, 0, tzinfo=timezone.utc))
        assert rl.remaining == 42

    def test_remaining_optional(self):
        """Some upstreams expose only ``reset_at`` (e.g. ``Retry-After``)."""
        from animedex.models.common import RateLimit

        rl = RateLimit(reset_at=datetime(2026, 5, 7, 10, 5, 0, tzinfo=timezone.utc))
        assert rl.remaining is None


class TestApiError:
    def test_is_exception(self):
        from animedex.models.common import ApiError

        with pytest.raises(ApiError):
            raise ApiError("boom")

    def test_carries_backend_and_reason(self):
        from animedex.models.common import ApiError

        err = ApiError("fail", backend="anilist", reason="rate-limited")
        assert err.backend == "anilist"
        assert err.reason == "rate-limited"

    def test_string_form(self):
        from animedex.models.common import ApiError

        err = ApiError("fail", backend="anilist", reason="rate-limited")
        s = str(err)
        assert "anilist" in s
        assert "rate-limited" in s
        assert "fail" in s


class TestAnimedexModelBase:
    def test_subclass_inherits_frozen_and_extra_ignore(self):
        from animedex.models.common import AnimedexModel

        class Sample(AnimedexModel):
            x: int

        sample = Sample.model_validate({"x": 1, "extraneous": "ignored"})
        assert sample.x == 1
        with pytest.raises(Exception):
            sample.x = 2

    def test_populate_by_name_enabled(self):
        """Backends often use camelCase upstream; we want field aliases."""
        from pydantic import Field

        from animedex.models.common import AnimedexModel

        class Sample(AnimedexModel):
            episode_count: int = Field(alias="episodeCount")

        loaded = Sample.model_validate({"episodeCount": 12})
        assert loaded.episode_count == 12
        loaded2 = Sample.model_validate({"episode_count": 13})
        assert loaded2.episode_count == 13


class TestModuleSelftest:
    def test_selftest_callable_runs(self):
        """``selftest()`` is what the diagnostic invokes; it must not raise."""
        from animedex.models import common

        result = common.selftest()
        assert result is None or result is True
