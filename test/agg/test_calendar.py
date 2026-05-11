"""Unit tests for aggregate calendar helper branches."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src(backend: str = "jikan") -> SourceTag:
    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


class TestCalendarHelpers:
    def test_current_season_uses_local_now_when_date_omitted(self, monkeypatch):
        import animedex.agg.calendar as calendar

        monkeypatch.setattr(calendar, "_now_local", lambda: datetime(2026, 4, 2, tzinfo=timezone.utc))
        assert calendar.current_anime_season() == "spring"

    def test_invalid_season_and_sources_raise_typed_errors(self):
        import animedex.agg.calendar as calendar
        from animedex.models.common import ApiError

        with pytest.raises(ApiError, match="unknown season"):
            calendar._normalise_season("monsoon")
        with pytest.raises(ApiError, match="unknown day"):
            calendar._normalise_day("noday")
        with pytest.raises(ApiError, match="unknown source"):
            calendar._select_sources("anilist,unknown")

    def test_date_windows_cover_all_day_variants(self):
        import animedex.agg.calendar as calendar

        today = date(2026, 5, 11)  # Monday
        assert calendar._date_window("all", today=today) == (today, date(2026, 5, 18))
        assert calendar._date_window("today", today=today) == (today, date(2026, 5, 12))
        assert calendar._date_window("tomorrow", today=today) == (date(2026, 5, 12), date(2026, 5, 13))
        assert calendar._date_window("wednesday", today=today) == (date(2026, 5, 13), date(2026, 5, 14))

    def test_jikan_day_filter_resolves_relative_days(self):
        import animedex.agg.calendar as calendar

        today = date(2026, 5, 11)
        assert calendar._jikan_filter_for_day("all", today=today) is None
        assert calendar._jikan_filter_for_day("today", today=today) == "monday"
        assert calendar._jikan_filter_for_day("tomorrow", today=today) == "tuesday"
        assert calendar._jikan_filter_for_day("friday", today=today) == "friday"

    def test_jikan_schedule_row_handles_missing_broadcast(self):
        import animedex.agg.calendar as calendar

        class Row:
            title = "Untimed"
            broadcast = None

        projected = calendar._jikan_schedule_row(Row(), _src())
        assert projected.title == "Untimed"
        assert projected.weekday is None
        assert projected.local_time is None

    def test_airing_sort_keys_cover_direct_common_and_fallback_rows(self):
        import animedex.agg.calendar as calendar
        from animedex.models.anime import AiringScheduleRow

        class Direct:
            airingAt = 10
            source_tag = _src("anilist")

        assert calendar._item_airing_key(Direct(), start=date(2026, 5, 11)) == (10, 0, "anilist")

        row = AiringScheduleRow(
            title="Exact",
            airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
            source=_src("jikan"),
        )
        assert calendar._item_airing_key(row, start=date(2026, 5, 11))[1] == 0

        row = AiringScheduleRow(title="Bad Time", weekday="monday", local_time="not-a-time", source=_src("jikan"))
        assert calendar._item_airing_key(row, start=date(2026, 5, 11))[1] == 1

        class Fallback:
            title = "zzz"

        assert calendar._item_airing_key(Fallback(), start=date(2026, 5, 11))[1] == 2

    def test_empty_fanout_returns_empty_envelope(self):
        import animedex.agg.calendar as calendar

        result = calendar._source_fanout([], lambda name: None)
        assert result.items == []
        assert result.sources == {}

    def test_package_and_calendar_selftests_run(self):
        import animedex.agg as agg
        import animedex.agg.calendar as calendar

        assert agg.selftest() is True
        assert calendar.selftest() is True
