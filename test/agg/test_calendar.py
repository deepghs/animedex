"""Tests for :mod:`animedex.agg.calendar` merge helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Optional

import pytest

from animedex.models.aggregate import AggregateResult, AggregateSourceStatus
from animedex.models.anime import AiringScheduleRow, Anime, AnimeTitle
from animedex.models.common import SourceTag

pytestmark = pytest.mark.unittest


def _source(name: str = "test") -> SourceTag:
    return SourceTag(backend=name, fetched_at=datetime(2026, 5, 11, tzinfo=timezone.utc))


def _anime(
    backend: str,
    ident: str,
    title: str,
    *,
    english: Optional[str] = None,
    native: Optional[str] = None,
    ids: Optional[dict] = None,
    season_year: Optional[int] = 2024,
    season: Optional[str] = "SPRING",
    format: Optional[str] = "TV",
    episodes: Optional[int] = 12,
    aired_from: Optional[date] = date(2024, 4, 1),
) -> Anime:
    return Anime(
        id=ident,
        title=AnimeTitle(romaji=title, english=english, native=native),
        ids=ids or {},
        source=_source(backend),
        season_year=season_year,
        season=season,
        format=format,
        episodes=episodes,
        aired_from=aired_from,
    )


def test_title_key_variants_use_multiple_transliterators():
    from animedex.agg import calendar

    japanese_keys = calendar._title_key_variants(
        "\u30bd\u30fc\u30c9\u30a2\u30fc\u30c8\u30fb\u30aa\u30f3\u30e9\u30a4\u30f3"
    )
    assert "so doa to onrain" in japanese_keys
    assert "sodoato onrain" in japanese_keys

    accented_keys = calendar._title_key_variants("Pok\u00e9mon")
    assert "pokemon" in accented_keys


def test_short_transliteration_keys_are_not_strong():
    from animedex.agg import calendar

    assert "8" in calendar._title_key_variants("\u602a\u7363\uff18\u53f7")
    assert not calendar._is_strong_title_key("8")
    assert not calendar._is_strong_title_key("no")


def test_season_merge_rule_matches_adjudicated_2010_2025_baseline():
    from animedex.agg import calendar
    from tools.merge_eval import evaluate_rule

    assert calendar.selftest() is True
    assert evaluate_rule.main(["--limit-details", "5"]) == 0


def test_timezone_helpers_cover_named_offset_and_errors(monkeypatch):
    from animedex.agg import calendar
    from animedex.models.common import ApiError

    class NamedOnlyTimezone(tzinfo):
        def utcoffset(self, dt):
            return None

        def tzname(self, dt):
            return "named-only"

        def dst(self, dt):
            return None

    local_tz = timezone(timedelta(hours=-5), name="fixed-local")
    monkeypatch.setattr(calendar, "_now_local", lambda: datetime(2026, 5, 11, tzinfo=local_tz))

    assert calendar._timezone_label(calendar.ZoneInfo("Asia/Tokyo")) == "Asia/Tokyo"
    assert calendar._timezone_label(timezone(timedelta(hours=2), name="custom")) == "+02:00"
    assert calendar._timezone_label(NamedOnlyTimezone()) == "named-only"
    assert calendar._resolve_timezone(None)[1] == "-05:00"
    assert calendar._resolve_timezone("-0230")[1] == "-02:30"
    assert calendar._jikan_source_timezone(None, target_tz=timezone.utc) is timezone.utc
    assert calendar._jikan_source_timezone("", target_tz=timezone.utc) is timezone.utc
    assert calendar._jikan_source_timezone("No/Such_Zone", target_tz=timezone.utc) is timezone.utc
    assert isinstance(calendar._now_local(), datetime)

    with pytest.raises(ApiError):
        calendar._resolve_timezone("+24:00")
    with pytest.raises(ApiError):
        calendar._resolve_timezone("No/Such_Zone")


def test_jikan_source_timezone_falls_back_when_zoneinfo_data_is_missing(monkeypatch):
    from animedex.agg import calendar

    def missing_zone(_name):
        raise calendar.ZoneInfoNotFoundError

    monkeypatch.setattr(calendar, "ZoneInfo", missing_zone)

    out = calendar._jikan_source_timezone("JST", target_tz=timezone.utc)

    assert out.utcoffset(datetime(2026, 5, 11)).total_seconds() == 9 * 3600


def test_date_window_and_schedule_filters_cover_relative_days():
    from animedex.agg import calendar

    base = date(2026, 5, 11)
    assert calendar._date_window("all", today=base) == (base, date(2026, 5, 18))
    assert calendar._date_window("today", today=base) == (base, date(2026, 5, 12))
    assert calendar._date_window("tomorrow", today=base) == (date(2026, 5, 12), date(2026, 5, 13))
    assert calendar._jikan_filters_for_day("all", today=base) == (None,)


def test_schedule_handles_empty_jikan_filter_set(monkeypatch):
    from animedex.agg import calendar

    monkeypatch.setattr(calendar, "_jikan_filters_for_day", lambda _day, *, today: ())

    out = calendar.schedule(day="today", source="jikan", timezone_name="UTC")

    assert out.items == []
    assert out.sources["jikan"].items == 0


def test_argument_normalizers_reject_unknown_values():
    from animedex.agg import calendar
    from animedex.models.common import ApiError

    with pytest.raises(ApiError):
        calendar._normalise_season("monsoon")
    with pytest.raises(ApiError):
        calendar._normalise_day("noday")
    with pytest.raises(ApiError):
        calendar._select_sources("jikan,unknown")


def test_jikan_schedule_row_uses_jst_timezone_data():
    from animedex.agg import calendar
    from animedex.backends.jikan.models import JikanGenericRow

    row = JikanGenericRow.model_validate(
        {
            "title": "Shin Nippon History",
            "broadcast": {"day": "Mondays", "time": "01:00", "timezone": "Asia/Tokyo"},
        }
    )

    out = calendar._jikan_schedule_row(row, _source("jikan"), start=date(2026, 5, 11), target_tz=timezone.utc)

    assert out.weekday == "sunday"
    assert out.local_time == "16:00"
    assert out.airing_at == datetime(2026, 5, 10, 16, 0, tzinfo=timezone.utc)


def test_jikan_schedule_row_without_conversion_keeps_broadcast_fields():
    from animedex.agg import calendar
    from animedex.backends.jikan.models import JikanGenericRow

    row = JikanGenericRow.model_validate({"name": "Fallback Name", "broadcast": {"day": "Mondays", "time": "01:00"}})

    out = calendar._jikan_schedule_row(row, _source("jikan"))

    assert out.title == "Fallback Name"
    assert out.weekday == "monday"
    assert out.local_time == "01:00"
    assert out.airing_at is None


def test_parse_clock_rejects_non_clock_values():
    from animedex.agg import calendar

    assert calendar._parse_clock(None) is None
    assert calendar._parse_clock("bad") is None


def test_item_datetime_covers_epoch_weekday_and_bad_time():
    from animedex.agg import calendar

    class DirectEpoch:
        airingAt = 1778457600

    weekday_row = AiringScheduleRow(title="Weekday", weekday="monday", local_time="01:02", source=_source())
    bad_row = AiringScheduleRow(title="Bad", weekday="monday", local_time="bad", source=_source())

    assert calendar._item_datetime(DirectEpoch(), start=date(2026, 5, 11), tz=timezone.utc) == datetime(
        2026, 5, 11, 0, 0, tzinfo=timezone.utc
    )
    assert calendar._item_datetime(weekday_row, start=date(2026, 5, 11), tz=timezone.utc) == datetime(
        2026, 5, 11, 1, 2, tzinfo=timezone.utc
    )
    assert calendar._item_datetime(bad_row, start=date(2026, 5, 11), tz=timezone.utc) == datetime(
        2026, 5, 11, 23, 59, tzinfo=timezone.utc
    )
    assert calendar._item_airing_key(object(), start=date(2026, 5, 11), tz=timezone.utc)[0] == 2**63 - 1


def test_filter_schedule_window_preserves_failed_source_status():
    from animedex.agg import calendar

    row = AiringScheduleRow(
        title="Outside",
        airing_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
        source=_source("jikan"),
    )
    failed = AggregateSourceStatus(backend="anilist", status="failed", reason="upstream-error")
    result = AggregateResult(
        items=[row],
        sources={"jikan": AggregateSourceStatus(backend="jikan", status="ok", items=1), "anilist": failed},
    )

    filtered = calendar._filter_schedule_window(
        result,
        start=date(2026, 5, 11),
        end=date(2026, 5, 12),
        tz=timezone.utc,
    )

    assert filtered.items == []
    assert filtered.sources["jikan"].items == 0
    assert filtered.sources["anilist"] is failed


def test_to_common_anime_handles_failures_and_non_anime():
    from animedex.agg import calendar

    class BrokenRich:
        def to_common(self):
            raise RuntimeError("bad mapper")

    class NonAnimeRich:
        def to_common(self):
            return object()

    assert calendar._to_common_anime(_anime("anilist", "anilist:1", "Title")) is not None
    assert calendar._to_common_anime(BrokenRich()) is None
    assert calendar._to_common_anime(NonAnimeRich()) is None


def test_title_and_context_scoring_cover_role_branches():
    from animedex.agg import calendar

    left = _anime("anilist", "anilist:1", "Romaji", english="Shared English", native="共通")
    right = _anime("jikan", "jikan:1", "Different", english="Shared English", native="共通")
    fuzzy = _anime("jikan", "jikan:2", "Romaji!")
    old = _anime("jikan", "jikan:3", "Romaji", aired_from=date(2025, 1, 1))
    no_id = _anime("jikan", "plain-id", "Other", ids={"mal": "1"})
    with_id = _anime("anilist", "anilist:9", "Other", ids={"mal": "1"})

    assert calendar._anime_title_keys(left)
    assert calendar._title_match_score(left, right) >= 50
    assert calendar._title_match_score(left, fuzzy) >= 45
    assert calendar._context_match_score(left, old) < calendar._context_match_score(left, fuzzy)
    assert calendar._anime_match_score(with_id, no_id) == 1000
    assert "jikan" in calendar._merge_group({"jikan": no_id}).ids


def test_merge_season_items_keeps_passthrough_items():
    from animedex.agg import calendar

    anilist = _anime("anilist", "anilist:1", "Shared", ids={"mal": "1"})
    jikan = _anime("jikan", "jikan:1", "Shared", ids={"mal": "1"})
    passthrough = object()
    result = AggregateResult(items=[anilist, jikan, passthrough])

    merged = calendar._merge_season_items(result)

    assert len(merged.items) == 2
    assert merged.items[0].ids["mal"] == "1"
    assert merged.items[1] is passthrough
