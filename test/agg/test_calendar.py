"""Tests for :mod:`animedex.agg.calendar` merge helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest

from animedex.models.aggregate import AggregateResult, AggregateSourceStatus
from animedex.models.anime import AiringScheduleRow, Anime, AnimeRating, AnimeTitle, NextAiringEpisode
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


def test_payload_and_title_language_helpers_cover_fallbacks():
    from animedex.agg import calendar

    payload = {"id": "raw:1"}

    assert calendar._model_payload(payload) == payload
    assert calendar._model_payload(payload) is not payload
    assert calendar._model_payload(object()) == {}
    assert calendar._language_from_title_type("Mandarin") == "chinese"
    assert calendar._language_from_title_type("KO") == "korean"


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

    local_tz = timezone(timedelta(hours=-5), name="fixed-local")
    monkeypatch.setattr(calendar, "_now_local", lambda: datetime(2026, 5, 11, tzinfo=local_tz))

    assert calendar._resolve_timezone(None)[1] == "-05:00"
    assert calendar._resolve_timezone("-0230")[1] == "-02:30"
    assert calendar._resolve_timezone("UTC+8")[1] == "+08:00"
    assert calendar._resolve_timezone("CST-8")[0].utcoffset(datetime(2026, 1, 1)).total_seconds() == 8 * 3600
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

    def missing_timezone(_name):
        raise ValueError("missing")

    monkeypatch.setattr(calendar, "parse_timezone", missing_timezone)

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
    assert out.details["backend"] == "jikan"
    assert out.details["broadcast_timezone"] == "Asia/Tokyo"


def test_jikan_schedule_row_without_conversion_keeps_broadcast_fields():
    from animedex.agg import calendar
    from animedex.backends.jikan.models import JikanGenericRow

    row = JikanGenericRow.model_validate({"name": "Fallback Name", "broadcast": {"day": "Mondays", "time": "01:00"}})

    out = calendar._jikan_schedule_row(row, _source("jikan"))

    assert out.title == "Fallback Name"
    assert out.weekday == "monday"
    assert out.local_time == "01:00"
    assert out.airing_at is None
    assert out.details["backend"] == "jikan"


def test_parse_clock_rejects_non_clock_values():
    from animedex.agg import calendar

    assert calendar._parse_clock(None) is None
    assert calendar._parse_clock("bad") is None


def test_raw_source_detail_helpers_cover_edge_and_empty_shapes():
    from animedex.agg import calendar

    class Named:
        def __init__(self, name, rank=None):
            self.name = name
            self.rank = rank

    class Edge:
        def __init__(self, node):
            self.node = node

    class Connection:
        edges = [Edge(Named("Edge Studio"))]

    class Raw:
        tags = [Named("", 1), Named("Magic", 80)]
        studios = [Named("Direct Studio")]

    class EdgeRaw:
        studios = Connection()

    record = _anime(
        "anilist",
        "anilist:adult",
        "Adult Title",
        ids={"anilist": "adult"},
    ).model_copy(
        update={
            "genres": ["Drama"],
            "tags": ["Slow Burn"],
            "is_adult": True,
            "score": AnimeRating(score=81.0, scale=100.0),
            "next_airing_episode": NextAiringEpisode(
                episode=4,
                airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
                time_until_airing_seconds=3600,
            ),
        }
    )

    details = calendar._anime_source_details(record, Raw())

    assert calendar._raw_tag_details(Raw()) == [{"name": "Magic", "rank": 80}]
    assert calendar._raw_studio_names(Raw()) == ["Direct Studio"]
    assert calendar._raw_studio_names(EdgeRaw()) == ["Edge Studio"]
    assert "adult" in details["type_tags"]
    assert details["next_airing_episode"]["episode"] == 4


def test_jikan_and_anilist_detail_helpers_keep_source_specific_tags():
    from animedex.agg import calendar

    class Named:
        def __init__(self, name):
            self.name = name

    class JikanRow:
        type = "TV"
        status = "Currently Airing"
        source = "Manga"
        rating = "PG-13"
        season = "spring"
        genres = [Named("Action")]
        explicit_genres = []
        themes = [Named("School")]
        demographics = [Named("Shounen")]

    media = {
        "type": "ANIME",
        "format": "TV",
        "status": "RELEASING",
        "season": "SPRING",
        "source": "MANGA",
        "genres": ["Action"],
        "tags": [{"name": "School", "rank": 80}, "bad-tag"],
        "isAdult": True,
        "studios": {"edges": [{"node": {"name": "Studio A"}}, {"node": {}}]},
    }

    assert {"Action", "School", "Shounen"} <= set(calendar._jikan_row_type_tags(JikanRow()))
    assert calendar._media_studio_names(media) == ["Studio A"]
    assert {"Action", "School", "adult"} <= set(calendar._anilist_media_type_tags(media))

    enriched = calendar._anilist_schedule_details_from_payload({"media": media}, {"media_id": 1})

    assert enriched["studios"] == ["Studio A"]
    assert "adult" in enriched["type_tags"]


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
        id = "broken:1"
        source_tag = _source("broken")

        def to_common(self):
            raise ValueError("bad mapper")

    class NonAnimeRich:
        def to_common(self):
            return object()

    assert calendar._to_common_anime(_anime("anilist", "anilist:1", "Title")) is not None
    assert calendar._to_common_anime(BrokenRich()) is None
    assert calendar._to_common_anime(NonAnimeRich()) is None


def test_merge_season_items_reports_to_common_failures():
    from animedex.agg import calendar

    class BrokenRich:
        id = "broken:1"
        source_tag = _source("broken")

        def to_common(self):
            raise KeyError("bad mapper")

    result = AggregateResult(items=[BrokenRich()])

    merged = calendar._merge_season_items(result)

    assert len(merged.items) == 1
    assert len(merged.merge_diagnostics) == 1
    assert merged.merge_diagnostics[0]["backend"] == "broken"
    assert merged.merge_diagnostics[0]["id"] == "broken:1"
    assert merged.merge_diagnostics[0]["reason"] == "to-common-failed"
    assert "KeyError" in merged.merge_diagnostics[0]["message"]


def test_schedule_projection_converts_rich_rows_to_common_rows():
    from animedex.agg import calendar
    from animedex.backends.anilist.models import AnilistAiringSchedule

    rich = AnilistAiringSchedule(
        id=99,
        airingAt=1778457600,
        episode=7,
        timeUntilAiring=300,
        media_id=123,
        media_title_romaji="Projected",
        source_tag=_source("anilist"),
    )
    result = AggregateResult(items=[rich])

    projected = calendar._project_schedule_items(result, target_tz=timezone(timedelta(hours=8)))

    row = projected.items[0]
    assert isinstance(row, AiringScheduleRow)
    assert row.title == "Projected"
    assert row.airing_at == datetime(2026, 5, 11, 8, 0, tzinfo=timezone(timedelta(hours=8)))
    assert row.details["backend"] == "anilist"
    assert row.details["media_id"] == 123


def test_schedule_projection_keeps_passthrough_items_and_drops_bad_common_rows():
    from animedex.agg import calendar

    class BrokenRich:
        def to_common(self):
            raise RuntimeError("bad mapper")

    class NonScheduleRich:
        def to_common(self):
            return object()

    passthrough = object()
    result = AggregateResult(items=[BrokenRich(), NonScheduleRich(), passthrough])

    assert calendar._to_common_schedule_row(BrokenRich()) is None
    assert calendar._to_common_schedule_row(NonScheduleRich()) is None

    projected = calendar._project_schedule_items(result, target_tz=timezone.utc)

    assert projected.items == result.items


def test_title_and_context_scoring_cover_role_branches():
    from animedex.agg import calendar

    left = _anime("anilist", "anilist:1", "Romaji", english="Shared English", native="\u5171\u901a")
    right = _anime("jikan", "jikan:1", "Different", english="Shared English", native="\u5171\u901a")
    fuzzy = _anime("jikan", "jikan:2", "Romaji!")
    old = _anime("jikan", "jikan:3", "Romaji", aired_from=date(2025, 1, 1))
    no_id = _anime("jikan", "plain-id", "Other", ids={"mal": "1"})
    with_id = _anime("anilist", "anilist:9", "Other", ids={"mal": "1"})
    conflicting_id = _anime("jikan", "jikan:10", "Other", ids={"mal": "2"})
    synonym = _anime("jikan", "jikan:11", "Shared Nickname")
    synonym_source = _anime("anilist", "anilist:11", "Official Title").model_copy(
        update={"title_synonyms": ["Shared Nickname"]}
    )
    fuzzy_92 = _anime("jikan", "jikan:12", "abcdefghijklmnopqrsu")
    fuzzy_92_source = _anime("anilist", "anilist:12", "abcdefghijklmnopqrst")
    episode_mismatch = _anime("jikan", "jikan:13", "Romaji", episodes=20)

    assert calendar._anime_title_keys(left)
    assert calendar._title_match_score(left, right) >= 50
    assert calendar._title_match_score(left, fuzzy) >= 45
    assert calendar._title_match_score(synonym_source, synonym) >= 35
    assert calendar._title_match_score(fuzzy_92_source, fuzzy_92) >= 35
    assert calendar._context_match_score(left, old) < calendar._context_match_score(left, fuzzy)
    assert calendar._context_match_score(left, episode_mismatch) < calendar._context_match_score(left, fuzzy)
    assert calendar._anime_match_score(with_id, no_id) == 1000
    assert calendar._anime_match_score(with_id, conflicting_id) == 0
    assert calendar._anime_match_score(left, fuzzy) >= 70
    assert (
        calendar._external_id_conflicts(
            with_id.model_copy(update={"ids": {"mal": None}}),
            no_id,
        )
        == []
    )
    assert "jikan" in calendar._merge_group({"jikan": no_id}).ids


def test_merge_season_items_splits_external_id_conflicts():
    from animedex.agg import calendar

    anilist = _anime("anilist", "anilist:1", "Shared Title", ids={"mal": "1"})
    jikan = _anime("jikan", "jikan:2", "Shared Title", ids={"mal": "2"})
    result = AggregateResult(items=[anilist, jikan])

    merged = calendar._merge_season_items(result)

    assert len(merged.items) == 2
    assert [item.ids["mal"] for item in merged.items] == ["1", "2"]
    assert [{source.backend for source in item.sources} for item in merged.items] == [{"anilist"}, {"jikan"}]


def test_merge_season_items_keeps_passthrough_items():
    from animedex.agg import calendar

    anilist = _anime("anilist", "anilist:1", "Shared", ids={"mal": "1"})
    jikan = _anime("jikan", "jikan:1", "Shared", ids={"mal": "1"})
    passthrough = object()
    result = AggregateResult(items=[anilist, jikan, passthrough])

    merged = calendar._merge_season_items(result)

    assert len(merged.items) == 2
    assert merged.items[0].ids["mal"] == "1"
    assert merged.items[0].source_details["anilist"]["title"] == "Shared"
    assert merged.items[0].source_details["jikan"]["format"] == "TV"
    assert merged.items[1] is passthrough


def test_merged_detail_helpers_keep_multilingual_and_conflict_guards():
    from animedex.agg import calendar

    title = AnimeTitle(romaji="Merged", english="Merged English", native="\u7d71\u5408")
    details = {
        "bad": {"titles": "not-a-dict"},
        "anilist": {
            "titles": {
                "typed": ["bad-entry", {"type": "Korean", "title": "\ud1b5\ud569"}],
                "by_language": {"chinese": ["\u6574\u5408"]},
            },
            "genres": ["Action", "Fantasy"],
        },
        "jikan": {"genres": ["Drama"]},
    }
    sparse = _anime("anilist", "anilist:sparse", "Sparse").model_copy(update={"ids": {"mal": None, "empty": ""}})
    left = _anime("anilist", "anilist:1", "Conflict", ids={"mal": "1"})
    right = _anime("jikan", "jikan:2", "Conflict", ids={"mal": "2"})

    titles = calendar._merged_title_details(title, details)

    assert titles["by_language"]["korean"] == ["\ud1b5\ud569"]
    assert titles["by_language"]["chinese"] == ["\u6574\u5408"]
    assert calendar._collect_unique_field(details, "genres", limit=2) == ["Action", "Fantasy"]
    assert "mal" not in calendar._merge_group({"anilist": sparse}).ids
    with pytest.raises(ValueError):
        calendar._merge_group({"anilist": left, "jikan": right})
