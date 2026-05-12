"""
Tests for :mod:`animedex.render.tty`.

The TTY renderer is what humans see at the terminal. Per ``plans/03
§5`` the source must always be visible to the human reader, so the
TTY path always emits ``[src: <backend>]`` annotations - there is no
``--source-attribution=off`` for TTY.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time, timezone

import pytest

from animedex.models.anime import Anime, AnimeTitle
from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _anime() -> Anime:
    return Anime(
        id="anilist:154587",
        title=AnimeTitle(romaji="Sousou no Frieren", english="Frieren: Beyond Journey's End"),
        episodes=28,
        studios=["Madhouse"],
        ids={"mal": "52991"},
        source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
    )


class TestRenderTty:
    def test_includes_source_marker(self):
        from animedex.render.tty import render_tty

        out = render_tty(_anime())
        assert "[src: anilist]" in out

    def test_includes_title_and_episodes(self):
        from animedex.render.tty import render_tty

        out = render_tty(_anime())
        assert "Sousou no Frieren" in out
        assert "28" in out


class TestPickRenderer:
    def test_atty_picks_tty(self, monkeypatch):
        from animedex.render.tty import is_terminal, render_for_stream

        class FakeStream:
            def isatty(self):
                return True

        out = render_for_stream(_anime(), FakeStream())
        assert "[src: anilist]" in out
        assert is_terminal(FakeStream()) is True

    def test_pipe_picks_json(self, monkeypatch):
        import json

        from animedex.render.tty import render_for_stream

        class FakeStream:
            def isatty(self):
                return False

        out = render_for_stream(_anime(), FakeStream())
        # The pipe path returns parseable JSON.
        decoded = json.loads(out)
        assert decoded["id"] == "anilist:154587"


class TestRenderTtyFullFields:
    def test_includes_score_and_streaming(self):
        from animedex.models.anime import (
            Anime,
            AnimeRating,
            AnimeStreamingLink,
            AnimeTitle,
        )
        from animedex.render.tty import render_tty

        a = Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="x"),
            score=AnimeRating(score=9.0, scale=10.0),
            streaming=[AnimeStreamingLink(provider="X", url="https://x.invalid/x")],
            ids={},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(a)
        assert "9.0/10.0" in out
        assert "Streaming:" in out and "X:" in out


class TestRenderAiringScheduleRow:
    def test_renders_schedule_row(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        row = AiringScheduleRow(
            title="Shin Nippon History",
            weekday="monday",
            local_time="01:00",
            source=SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(row)
        assert "Shin Nippon History" in out
        assert "[src: jikan]" in out
        assert "Schedule: monday" in out

    def test_renders_airing_instant_and_episode(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        row = AiringScheduleRow(
            title="Exact Airing",
            airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
            episode=3,
            details={"score": 8.2, "source_material": "Manga", "genres": ["Action"]},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(row)
        assert "Airing:" in out
        assert "Episode:  3" in out
        assert "Info:" in out
        assert "Source material: Manga" in out
        assert "Score: 8.2" in out

    def test_renders_schedule_ids(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        row = AiringScheduleRow(
            title="Exact Airing",
            airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
            episode=3,
            core={"media_id": 181284},
            details={"schedule_id": 12345, "media_id": 181284, "mal_id": 999},
            source_payload={"id": 12345, "media": {"id": 181284, "idMal": 999}},
            source=SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(row)
        assert "IDs:" in out
        assert "AniList airing: 12345" in out
        assert "AniList media: 181284" in out
        assert "MAL: 999" in out

    def test_renders_schedule_ids_from_core_and_unknown_backend(self):
        from animedex.models.anime import AiringScheduleRow
        from animedex.render.tty import render_tty

        core = render_tty(
            AiringScheduleRow(
                title="Core IDs",
                core={"ids": {"jikan": "777"}},
                source=SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
            )
        )
        custom = render_tty(
            AiringScheduleRow(
                title="Custom IDs",
                details={"id": "custom-1"},
                source=SourceTag(backend="custom_backend", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
            )
        )

        assert "Jikan: 777" in core
        assert "Custom backend: custom-1" in custom

    def test_renders_nested_tree_values_and_limits(self):
        from animedex.render import tty

        out = io.StringIO()
        list_out = io.StringIO()
        tty._render_tree(
            out,
            "",
            {
                "": "fallback label",
                "date": date(2026, 5, 11),
                "time": time(1, 2),
                "flag": True,
                "empty": "",
                "nested": {"alpha": "a", "empty": None},
                "list": [{"name": "one"}, ["two"], "three", "", "four"],
                "extra": "hidden",
            },
            indent=0,
            limit=6,
        )
        tty._render_tree(list_out, "Items", [["nested"], "plain", "extra"], indent=0, limit=2)
        compact = tty._compact_tree({"empty": "", "items": [{"name": "one"}, "two", {}], "nested": {"value": False}})

        text = out.getvalue()
        list_text = list_out.getvalue()

        assert "Value: fallback label" in text
        assert "Date: 2026-05-11" in text
        assert "Time: 01:02:00" in text
        assert "Flag: true" in text
        assert "Nested:" in text
        assert "List:" in text
        assert "(+1 more)" in text
        assert "- nested" in list_text
        assert "- plain" in list_text
        assert "- (+1 more)" in list_text
        assert compact == {"items": [{"name": "one"}, "two"], "nested": {"value": False}}

    def test_tree_and_summary_helpers_cover_empty_and_non_list_inputs(self):
        from animedex.render import tty

        out = io.StringIO()
        tty._render_tree(out, "Empty", "", indent=0)

        assert out.getvalue() == ""
        assert tty._limited_unique("not-a-list") == []
        assert tty._filtered_tags("not-a-list") == []
        assert tty._join_summary("ready") == "ready"
        assert tty._join_summary(object()) is None
        assert tty._first_text(["", " first "]) == "first"


class TestRenderAggregateResult:
    def test_empty_aggregate_renders_empty_string(self):
        from animedex.models.aggregate import AggregateResult
        from animedex.render.tty import render_tty

        assert render_tty(AggregateResult()) == ""

    def test_aggregate_renders_plain_non_model_items(self):
        from animedex.models.aggregate import AggregateResult
        from animedex.render.tty import render_tty

        assert render_tty(AggregateResult(items=["plain"])) == "plain"


class TestRenderScheduleCalendar:
    def test_empty_calendar_renders_header_only(self):
        from animedex.models.aggregate import ScheduleCalendarResult
        from animedex.render.tty import render_tty

        out = render_tty(
            ScheduleCalendarResult(
                items=[],
                sources={},
                timezone="UTC",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )

        assert out == "Schedule (UTC)\nWindow: 2026-05-11 to 2026-05-12 (exclusive)\n"

    def test_calendar_renders_offsets_iana_unknowns_rich_rows_and_floating_items(self):
        from animedex.models.aggregate import ScheduleCalendarResult
        from animedex.models.anime import AiringScheduleRow
        from animedex.models.common import BackendRichModel
        from animedex.render.tty import render_tty

        src = SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))

        class _RichSchedule(BackendRichModel):
            source_tag: SourceTag

            def to_common(self):
                return AiringScheduleRow(title="Rich Row", weekday="monday", local_time="02:30", source=src)

        class _BrokenRichSchedule(BackendRichModel):
            source_tag: SourceTag

            def to_common(self):
                raise RuntimeError("bad mapper")

        offset = render_tty(
            ScheduleCalendarResult(
                items=[
                    AiringScheduleRow(
                        title="Episode Row",
                        weekday="monday",
                        local_time="01:00",
                        episode=7,
                        source=src,
                        details={"source_material": "Original", "rating": "G"},
                    ),
                    AiringScheduleRow(title="Bad Clock", weekday="monday", local_time="bad", source=src),
                    _RichSchedule(source_tag=src),
                    _BrokenRichSchedule(source_tag=src),
                    "floating text",
                ],
                sources={},
                timezone="-02:30",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )

        assert "Monday, 2026-05-11" in offset
        assert "01:00  Episode Row  ep 7  [src: jikan]" in offset
        assert "Info:" in offset
        assert "Source material: Original" in offset
        assert "Rating: G" in offset
        assert "02:30  Rich Row  [src: jikan]" in offset
        assert "Unscheduled" in offset
        assert "bad  Bad Clock  [src: jikan]" in offset
        assert '"source_tag"' in offset
        assert "floating text" in offset

        iana = render_tty(
            ScheduleCalendarResult(
                items=[
                    AiringScheduleRow(
                        title="Instant Row",
                        airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
                        source=src,
                    )
                ],
                sources={},
                timezone="Asia/Tokyo",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )
        assert "10:00  Instant Row  [src: jikan]" in iana

        utc = render_tty(
            ScheduleCalendarResult(
                items=[
                    AiringScheduleRow(
                        title="UTC Row",
                        airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
                        source=src,
                    )
                ],
                sources={},
                timezone="UTC",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )
        assert "01:00  UTC Row  [src: jikan]" in utc

        unknown = render_tty(
            ScheduleCalendarResult(
                items=[
                    AiringScheduleRow(
                        title="Naive Fallback",
                        airing_at=datetime(2026, 5, 11, 1, tzinfo=timezone.utc),
                        source=src,
                    )
                ],
                sources={},
                timezone="No/Such_Zone",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )
        assert "01:00  Naive Fallback  [src: jikan]" in unknown

        unscheduled = render_tty(
            ScheduleCalendarResult(
                items=[AiringScheduleRow(title="Loose Row", source=src)],
                sources={},
                timezone="UTC",
                window_start=date(2026, 5, 11),
                window_end=date(2026, 5, 12),
            )
        )
        assert "Unscheduled" in unscheduled
        assert "--:--  Loose Row  [src: jikan]" in unscheduled


class TestRenderMergedAnime:
    def test_renders_source_details(self):
        from animedex.models.aggregate import MergedAnime
        from animedex.models.anime import Anime, AnimeRating, AnimeTitle
        from animedex.render.tty import render_tty

        src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        anime = Anime(
            id="anilist:1",
            title=AnimeTitle(romaji="Merged"),
            score=AnimeRating(score=81.0, scale=100.0),
            ids={"anilist": "1"},
            source=src,
        )
        out = render_tty(
            MergedAnime(
                title=AnimeTitle(romaji="Merged"),
                sources=[src],
                records={"anilist": anime},
                source_details={
                    "anilist": {
                        "title": "Merged",
                        "titles": {
                            "romaji": "Merged",
                            "english": "Merged English",
                            "native": "\u7d71\u5408",
                            "by_language": {
                                "japanese": ["\u7d71\u5408"],
                                "chinese": ["\u6574\u5408"],
                                "korean": ["\ud1b5\ud569"],
                            },
                        },
                        "score": {"score": 81.0, "scale": 100.0},
                        "format": "TV",
                        "episodes": 12,
                        "season": "SPRING",
                        "season_year": 2024,
                        "studios": ["Studio A"],
                        "genres": ["Action", "Fantasy"],
                    }
                },
            )
        )

        assert "Names:" in out
        assert "Japanese:" in out
        assert "Chinese:" in out
        assert "Korean:" in out
        assert "IDs:" in out
        assert "AniList: 1" in out
        assert "Info:" in out
        assert "Season: SPRING 2024" in out
        assert "Scores:" in out
        assert "Anilist:" in out and "81.0/100.0" in out

    def test_renders_ids_from_records_and_source_details(self):
        from animedex.models.aggregate import MergedAnime
        from animedex.render.tty import render_tty

        anilist_src = SourceTag(backend="anilist", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        jikan_src = SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        anilist = Anime(
            id="anilist:10",
            title=AnimeTitle(romaji="Merged"),
            ids={"mal": "20"},
            source=anilist_src,
        )
        jikan = Anime(id="plain-jikan", title=AnimeTitle(romaji="Merged"), ids={}, source=jikan_src)
        out = render_tty(
            MergedAnime.model_construct(
                title=AnimeTitle(romaji="Merged"),
                sources=[anilist_src, jikan_src],
                records={"anilist": anilist, "jikan": jikan},
                core={"ids": {"kitsu": "40"}},
                source_details={
                    "anilist": {"id": "anilist:10", "ids": {"ann": "30"}},
                    "jikan": {"id": "detail-jikan"},
                    "broken": "not-a-dict",
                },
            )
        )

        assert "AniList: 10" in out
        assert "MAL: 20" in out
        assert "Jikan: plain-jikan" in out
        assert "ANN: 30" in out
        assert "Kitsu: 40" in out

    def test_renders_fallback_titles_and_airing_detail_shapes(self):
        from animedex.models.aggregate import MergedAnime
        from animedex.render.tty import render_tty

        src = SourceTag(backend="jikan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))
        anime = Anime(id="jikan:1", title=AnimeTitle(romaji="Merged"), ids={"mal": "1"}, source=src)
        out = render_tty(
            MergedAnime.model_construct(
                title=AnimeTitle(romaji="Merged"),
                sources=[src],
                records={"jikan": anime},
                core={"airing": {"season": "FALL", "aired_from": "2026-10-01"}},
                source_details={
                    "skip": "not-a-dict",
                    "jikan": {
                        "titles": {
                            "english": "Merged English",
                            "by_language": {"english": ["Merged English"], "japanese": ["\u7d71\u5408"]},
                            "native": "\u7d71\u5408",
                        },
                        "airing": {"season": "FALL"},
                        "aired_from": "2026-10-01",
                        "type_tags": ["TV", "finished", "Manga", "PG-13", "School"],
                        "genres": ["Drama"],
                        "score": {"score": 8.0},
                    },
                },
            )
        )

        assert "Names:" in out
        assert "English: Merged English" in out
        assert "Japanese: \u7d71\u5408" in out
        assert "Season: FALL" in out
        assert "Aired: 2026-10-01 to ongoing" in out
        assert "Scores:" in out
        assert "Jikan: 8.0" in out
        assert "Tags:" in out

    def test_airing_summary_helpers_cover_detail_fallbacks(self):
        from animedex.render import tty

        detail_values = {
            "one": {"genres": ["A", "B"]},
            "skip": "not-a-dict",
            "two": {"genres": ["C", "D"]},
        }

        assert tty._first_source_details({"skip": "not-a-dict"}) == {}
        assert tty._collect_source_detail_values(detail_values, "genres", limit=3) == ["A", "B", "C"]
        assert tty._season_text({}, {"season": "FALL"}) == "FALL"
        assert tty._date_range_text({"aired_from": "2026-10-01"}) == "2026-10-01 to ongoing"


class TestRenderTtyNonAnime:
    def test_falls_back_with_source_marker(self):
        from animedex.models.quote import Quote
        from animedex.render.tty import render_tty

        q = Quote(
            text="x",
            source=SourceTag(backend="animechan", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        )
        out = render_tty(q)
        assert "Quote" in out
        assert "[src: animechan]" in out


class TestRenderTtyFallbackHonorsAliases:
    """Reviewer review B2 (PR #6).

    The rich-model fallback path in ``render_tty`` (the ``hasattr
    to_common`` branch's last line) calls ``model_dump_json()``
    without ``by_alias=True``. So a rich model with aliased fields
    (e.g. ``RawTraceHit.from_`` aliased to ``from``) used to render
    ``\"from_\": ...`` instead of ``\"from\": ...``. AGENTS §13.6
    declares the renderer's output as a legitimate downstream shape;
    this drift broke the lossless contract.

    A rich model whose ``to_common()`` returns a non-renderable shape
    falls into the JSON-dump fallback path; we synthesize that case
    here.
    """

    def test_fallback_dump_uses_upstream_aliases(self):
        from animedex.models.common import BackendRichModel, SourceTag
        from animedex.render.tty import render_tty
        from pydantic import Field

        # A rich model with aliased fields whose ``to_common()`` returns
        # something the dispatcher doesn't recognise (so we land in the
        # JSON-dump fallback).
        class _RichWithAlias(BackendRichModel):
            from_: float = Field(alias="from")
            to_: float = Field(alias="to")
            source_tag: SourceTag

            def to_common(self):
                return None

        m = _RichWithAlias.model_validate(
            {
                "from": 832.7,
                "to": 836.8,
                "source_tag": SourceTag(backend="trace", fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
            }
        )
        out = render_tty(m)
        assert '"from"' in out, f"expected upstream alias 'from' in TTY fallback dump, got: {out!r}"
        assert '"to"' in out
        assert '"from_"' not in out
        assert '"to_"' not in out


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import tty

        assert tty.selftest() is True
