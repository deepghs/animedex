"""Calendar aggregate commands over AniList and Jikan.

This module composes the existing high-level backend APIs into
multi-source calendar results. It owns only selection, date/season
inference, and per-source fan-out; backend-specific request logic
stays under :mod:`animedex.backends`.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable, Optional, Sequence, Tuple

from animedex.agg._fanout import FanoutSource, run_fanout
from animedex.backends import anilist as _anilist
from animedex.backends import jikan as _jikan
from animedex.config import Config
from animedex.models.anime import AiringScheduleRow
from animedex.models.aggregate import AggregateResult
from animedex.models.common import ApiError, SourceTag


SEASONS: Tuple[str, ...] = ("winter", "spring", "summer", "fall")
SOURCES: Tuple[str, ...] = ("anilist", "jikan")
WEEKDAYS: Tuple[str, ...] = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAYS: Tuple[str, ...] = (*WEEKDAYS, "today", "tomorrow", "all")


def _now_local() -> datetime:
    return datetime.now().astimezone()


def current_anime_season(today: Optional[date] = None) -> str:
    """Return the local-month anime season.

    Anime calendar seasons follow the AniList/MAL quarterly convention:
    winter is January-March, spring is April-June, summer is
    July-September, and fall is October-December.

    :param today: Optional date override for callers that already have
                  one.
    :type today: datetime.date or None
    :return: Lowercase season name.
    :rtype: str
    """
    d = today if today is not None else _now_local().date()
    return SEASONS[(d.month - 1) // 3]


def _normalise_season(value: Optional[str]) -> str:
    out = current_anime_season() if value is None else value.lower()
    if out not in SEASONS:
        raise ApiError(
            f"unknown season: {value!r}; expected one of {', '.join(SEASONS)}",
            backend="aggregate",
            reason="bad-args",
        )
    return out


def _normalise_day(value: str) -> str:
    out = value.lower()
    if out not in DAYS:
        raise ApiError(
            f"unknown day: {value!r}; expected monday..sunday, today, tomorrow, or all",
            backend="aggregate",
            reason="bad-args",
        )
    return out


def _select_sources(source: str) -> Tuple[str, ...]:
    raw = [part.strip().lower() for part in source.split(",") if part.strip()]
    if not raw or raw == ["all"]:
        return SOURCES
    if "all" in raw and len(raw) > 1:
        raise ApiError("--source all cannot be combined with explicit sources", backend="aggregate", reason="bad-args")
    unknown = sorted(set(raw) - set(SOURCES))
    if unknown:
        raise ApiError(
            f"unknown source(s): {', '.join(unknown)}; expected anilist, jikan, or all",
            backend="aggregate",
            reason="bad-args",
        )
    selected = []
    for item in raw:
        if item not in selected:
            selected.append(item)
    return tuple(selected)


def _date_window(day: str, *, today: Optional[date] = None) -> Tuple[date, date]:
    base = today if today is not None else _now_local().date()
    if day == "all":
        return base, base + timedelta(days=7)
    if day == "today":
        return base, base + timedelta(days=1)
    if day == "tomorrow":
        start = base + timedelta(days=1)
        return start, start + timedelta(days=1)
    target = WEEKDAYS.index(day)
    delta = (target - base.weekday()) % 7
    start = base + timedelta(days=delta)
    return start, start + timedelta(days=1)


def _epoch_window(start: date, end: date) -> Tuple[int, int]:
    tz = _now_local().tzinfo
    start_dt = datetime.combine(start, time.min, tzinfo=tz)
    end_dt = datetime.combine(end, time.min, tzinfo=tz)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def _jikan_filter_for_day(day: str, *, today: Optional[date] = None) -> Optional[str]:
    if day == "all":
        return None
    if day in ("today", "tomorrow"):
        start, _end = _date_window(day, today=today)
        return WEEKDAYS[start.weekday()]
    return day


def _jikan_schedule_row(row, source_tag: SourceTag) -> AiringScheduleRow:
    title = getattr(row, "title", None) or getattr(row, "name", None) or "Untitled"
    broadcast = getattr(row, "broadcast", None)
    weekday = None
    local_time = None
    if isinstance(broadcast, dict):
        day = broadcast.get("day")
        if isinstance(day, str):
            weekday = day.lower().rstrip("s")
        time_text = broadcast.get("time")
        if isinstance(time_text, str):
            local_time = time_text
    return AiringScheduleRow(title=title, weekday=weekday, local_time=local_time, source=source_tag)


def _jikan_schedule_rows(response) -> list:
    return [_jikan_schedule_row(row, response.source_tag) for row in response.rows]


def _item_airing_key(item: object, *, start: date) -> Tuple[int, int, str]:
    source_tag = getattr(item, "source", None) or getattr(item, "source_tag", None)
    source = getattr(source_tag, "backend", "")
    direct = getattr(item, "airingAt", None)
    if isinstance(direct, int):
        return direct, 0, source
    if isinstance(item, AiringScheduleRow):
        if item.airing_at is not None:
            return int(item.airing_at.timestamp()), 0, source
        if item.weekday in WEEKDAYS:
            try:
                hour, minute = [int(part) for part in str(item.local_time or "23:59").split(":", 1)]
            except ValueError:
                hour, minute = 23, 59
            delta = (WEEKDAYS.index(item.weekday) - start.weekday()) % 7
            tz = _now_local().tzinfo
            return (
                int(datetime.combine(start + timedelta(days=delta), time(hour, minute), tzinfo=tz).timestamp()),
                1,
                source,
            )
    title = getattr(item, "media_title_romaji", None) or getattr(item, "title", None) or ""
    return 2**63 - 1, 2, str(title)


def _sort_schedule_items(result: AggregateResult, *, start: date) -> AggregateResult:
    return result.model_copy(
        update={"items": sorted(result.items, key=lambda item: _item_airing_key(item, start=start))}
    )


def _source_fanout(selected: Sequence[str], source_factory: Callable[[str], FanoutSource]) -> AggregateResult:
    return run_fanout([source_factory(name) for name in selected], max_workers=len(selected))


def season(
    year: Optional[int] = None,
    season: Optional[str] = None,
    *,
    source: str = "all",
    limit: int = 25,
    config: Optional[Config] = None,
    **kw,
) -> AggregateResult:
    """Return anime airing in a season from AniList and Jikan.

    :param year: Calendar year. Defaults to the current local year.
    :type year: int or None
    :param season: One of ``winter``, ``spring``, ``summer``, or
                   ``fall``. Defaults to the local-month anime season.
    :type season: str or None
    :param source: Comma-separated source allowlist: ``all``,
                   ``anilist``, ``jikan``, or a comma list.
    :type source: str
    :param limit: Per-source row limit.
    :type limit: int
    :param config: Optional runtime config.
    :type config: Config or None
    :return: Aggregate envelope.
    :rtype: AggregateResult
    """
    if limit < 1:
        raise ApiError("--limit must be >= 1", backend="aggregate", reason="bad-args")
    selected = _select_sources(source)
    resolved_year = _now_local().year if year is None else year
    resolved_season = _normalise_season(season)

    def _factory(name: str) -> FanoutSource:
        if name == "anilist":
            return FanoutSource(
                "anilist",
                lambda: _anilist.schedule(resolved_year, resolved_season.upper(), per_page=limit, config=config, **kw),
            )
        return FanoutSource(
            "jikan",
            lambda: _jikan.season(resolved_year, resolved_season, limit=limit, config=config, **kw),
        )

    return _source_fanout(selected, _factory)


def schedule(
    *,
    day: str = "all",
    source: str = "all",
    limit: int = 25,
    config: Optional[Config] = None,
    **kw,
) -> AggregateResult:
    """Return airing rows for a day or the upcoming seven-day window.

    :param day: ``monday`` through ``sunday``, ``today``,
                ``tomorrow``, or ``all``.
    :type day: str
    :param source: Comma-separated source allowlist.
    :type source: str
    :param limit: Per-source row limit.
    :type limit: int
    :param config: Optional runtime config.
    :type config: Config or None
    :return: Aggregate envelope.
    :rtype: AggregateResult
    """
    if limit < 1:
        raise ApiError("--limit must be >= 1", backend="aggregate", reason="bad-args")
    resolved_day = _normalise_day(day)
    selected = _select_sources(source)
    start, end = _date_window(resolved_day)
    lower, upper = _epoch_window(start, end)
    jikan_filter = _jikan_filter_for_day(resolved_day)

    def _factory(name: str) -> FanoutSource:
        if name == "anilist":
            return FanoutSource(
                "anilist",
                lambda: _anilist.airing_schedule(
                    airing_at_greater=lower,
                    airing_at_lesser=upper,
                    per_page=limit,
                    config=config,
                    **kw,
                ),
            )

        def _jikan_rows():
            return _jikan_schedule_rows(_jikan.schedules(filter=jikan_filter, limit=limit, config=config, **kw))

        return FanoutSource("jikan", _jikan_rows)

    return _sort_schedule_items(_source_fanout(selected, _factory), start=start)


def selftest() -> bool:
    """Smoke-test calendar parsing helpers without network access.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert current_anime_season(date(2026, 1, 1)) == "winter"
    assert current_anime_season(date(2026, 4, 1)) == "spring"
    assert current_anime_season(date(2026, 7, 1)) == "summer"
    assert current_anime_season(date(2026, 10, 1)) == "fall"
    assert _select_sources("jikan,anilist,jikan") == ("jikan", "anilist")
    assert _normalise_day("Today") == "today"
    return True
