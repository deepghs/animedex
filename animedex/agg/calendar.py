"""Calendar aggregate commands over AniList and Jikan.

This module composes the existing high-level backend APIs into
multi-source calendar results. It owns only selection, date/season
inference, and per-source fan-out; backend-specific request logic
stays under :mod:`animedex.backends`.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from difflib import SequenceMatcher
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jaconv
from anyascii import anyascii
from unidecode import unidecode

from animedex.agg._fanout import FanoutSource, run_fanout
from animedex.backends import anilist as _anilist
from animedex.backends import jikan as _jikan
from animedex.config import Config
from animedex.models.anime import AiringScheduleRow, Anime, AnimeTitle
from animedex.models.aggregate import AggregateResult, MergedAnime, ScheduleCalendarResult
from animedex.models.common import ApiError, SourceTag


SEASONS: Tuple[str, ...] = ("winter", "spring", "summer", "fall")
SOURCES: Tuple[str, ...] = ("anilist", "jikan")
WEEKDAYS: Tuple[str, ...] = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAYS: Tuple[str, ...] = (*WEEKDAYS, "today", "tomorrow", "all")
_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_TITLE_KEY_RE = re.compile(r"[^0-9a-z]+")
_MERGE_THRESHOLD = 70
_WEAK_TITLE_KEYS = frozenset({"x", "ii", "iii", "iv", "v"})
_TOKYO_TZ_ALIASES = frozenset({"asia/tokyo", "jst", "utc+9", "utc+09:00"})


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _timezone_label(tz: tzinfo) -> str:
    key = getattr(tz, "key", None)
    if isinstance(key, str) and key:
        return key
    if tz is timezone.utc:
        return "UTC"
    sample = _now_local()
    offset = tz.utcoffset(sample)
    if offset is not None:
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{sign}{hours:02d}:{minutes:02d}"
    name = tz.tzname(sample)
    return name or "local"


def _jikan_source_timezone(name: Optional[str], *, target_tz: Optional[tzinfo] = None) -> Optional[tzinfo]:
    if not isinstance(name, str):
        return target_tz
    normalized = name.strip().lower()
    if not normalized:
        return target_tz
    if normalized in _TOKYO_TZ_ALIASES:
        try:
            return ZoneInfo("Asia/Tokyo")
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=9), name="JST")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return target_tz


def _resolve_timezone(value: Optional[str]) -> Tuple[tzinfo, str]:
    raw = (value or "local").strip()
    if not raw or raw.lower() == "local":
        tz = _now_local().tzinfo or timezone.utc
        return tz, _timezone_label(tz)
    if raw.upper() in ("UTC", "Z"):
        return timezone.utc, "UTC"
    match = _OFFSET_RE.match(raw)
    if match is not None:
        sign, hours_text, minutes_text = match.groups()
        hours = int(hours_text)
        minutes = int(minutes_text)
        if hours > 23 or minutes > 59:
            raise ApiError(
                f"unknown timezone: {value!r}; expected local, UTC, an IANA name, or an offset like +08:00",
                backend="aggregate",
                reason="bad-args",
            )
        delta = timedelta(hours=hours, minutes=minutes)
        if sign == "-":
            delta = -delta
        label = f"{sign}{hours:02d}:{minutes:02d}"
        return timezone(delta, name=label), label
    try:
        return ZoneInfo(raw), raw
    except ZoneInfoNotFoundError as exc:
        raise ApiError(
            f"unknown timezone: {value!r}; expected local, UTC, an IANA name, or an offset like +08:00",
            backend="aggregate",
            reason="bad-args",
        ) from exc


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


def _epoch_window(start: date, end: date, tz: Optional[tzinfo] = None) -> Tuple[int, int]:
    tz = tz or _now_local().tzinfo or timezone.utc
    start_dt = datetime.combine(start, time.min, tzinfo=tz)
    end_dt = datetime.combine(end, time.min, tzinfo=tz)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def _jikan_filters_for_day(day: str, *, today: Optional[date] = None) -> Tuple[Optional[str], ...]:
    if day == "all":
        return (None,)
    start, end = _date_window(day, today=today)
    selected = []
    current = start - timedelta(days=1)
    while current <= end:
        weekday = WEEKDAYS[current.weekday()]
        if weekday not in selected:
            selected.append(weekday)
        current += timedelta(days=1)
    return tuple(selected)


def _parse_clock(value: object) -> Optional[time]:
    if not isinstance(value, str):
        return None
    try:
        hour, minute = [int(part) for part in value.split(":", 1)]
        return time(hour, minute)
    except (TypeError, ValueError):
        return None


def _jikan_schedule_row(
    row,
    source_tag: SourceTag,
    *,
    start: Optional[date] = None,
    target_tz: Optional[tzinfo] = None,
) -> AiringScheduleRow:
    title = getattr(row, "title", None) or getattr(row, "name", None) or "Untitled"
    broadcast = getattr(row, "broadcast", None)
    weekday = None
    local_time = None
    airing_at = None
    if isinstance(broadcast, dict):
        day = broadcast.get("day")
        if isinstance(day, str):
            weekday = day.lower().rstrip("s")
        time_text = broadcast.get("time")
        if isinstance(time_text, str):
            local_time = time_text
        source_tz_name = broadcast.get("timezone")
        source_tz = _jikan_source_timezone(source_tz_name, target_tz=target_tz)
        clock = _parse_clock(time_text)
        if start is not None and target_tz is not None and weekday in WEEKDAYS and clock is not None:
            source_tz = source_tz or target_tz
            delta = (WEEKDAYS.index(weekday) - start.weekday()) % 7
            source_dt = datetime.combine(start + timedelta(days=delta), clock, tzinfo=source_tz)
            target_dt = source_dt.astimezone(target_tz)
            airing_at = target_dt
            weekday = WEEKDAYS[target_dt.weekday()]
            local_time = target_dt.strftime("%H:%M")
    return AiringScheduleRow(
        title=title,
        airing_at=airing_at,
        weekday=weekday,
        local_time=local_time,
        source=source_tag,
    )


def _jikan_schedule_rows(response, *, start: Optional[date] = None, target_tz: Optional[tzinfo] = None) -> list:
    return [_jikan_schedule_row(row, response.source_tag, start=start, target_tz=target_tz) for row in response.rows]


def _item_datetime(item: object, *, start: date, tz: Optional[tzinfo] = None) -> Optional[datetime]:
    direct = getattr(item, "airingAt", None)
    if isinstance(direct, int):
        return (
            datetime.fromtimestamp(direct, tz=timezone.utc).astimezone(tz)
            if tz is not None
            else datetime.fromtimestamp(direct, tz=timezone.utc)
        )
    if isinstance(item, AiringScheduleRow):
        if item.airing_at is not None:
            return item.airing_at.astimezone(tz) if tz is not None else item.airing_at
        if item.weekday in WEEKDAYS:
            try:
                hour, minute = [int(part) for part in str(item.local_time or "23:59").split(":", 1)]
            except ValueError:
                hour, minute = 23, 59
            delta = (WEEKDAYS.index(item.weekday) - start.weekday()) % 7
            return datetime.combine(start + timedelta(days=delta), time(hour, minute), tzinfo=tz)
    return None


def _item_airing_key(item: object, *, start: date, tz: Optional[tzinfo] = None) -> Tuple[int, int, str]:
    source_tag = getattr(item, "source", None) or getattr(item, "source_tag", None)
    source = getattr(source_tag, "backend", "")
    when = _item_datetime(item, start=start, tz=tz or _now_local().tzinfo or timezone.utc)
    if when is not None:
        return int(when.timestamp()), 0 if getattr(item, "airing_at", None) is not None else 1, source
    title = getattr(item, "media_title_romaji", None) or getattr(item, "title", None) or ""
    return 2**63 - 1, 2, str(title)


def _sort_schedule_items(result: AggregateResult, *, start: date, tz: Optional[tzinfo] = None) -> AggregateResult:
    return result.model_copy(
        update={"items": sorted(result.items, key=lambda item: _item_airing_key(item, start=start, tz=tz))}
    )


def _filter_schedule_window(result: AggregateResult, *, start: date, end: date, tz: tzinfo) -> AggregateResult:
    kept_by_source: Dict[str, int] = {name: 0 for name in result.sources}
    kept_items = []
    for item in result.items:
        when = _item_datetime(item, start=start, tz=tz)
        if when is None or not (start <= when.date() < end):
            continue
        kept_items.append(item)
        source_tag = getattr(item, "source", None) or getattr(item, "source_tag", None)
        source_name = getattr(source_tag, "backend", None)
        if source_name in kept_by_source:
            kept_by_source[source_name] += 1

    sources = {}
    for name, status in result.sources.items():
        if status.ok:
            sources[name] = status.model_copy(update={"items": kept_by_source.get(name, 0)})
        else:
            sources[name] = status
    return result.model_copy(update={"items": kept_items, "sources": sources})


def _source_fanout(selected: Sequence[str], source_factory: Callable[[str], FanoutSource]) -> AggregateResult:
    return run_fanout([source_factory(name) for name in selected], max_workers=len(selected))


def _to_common_anime(item: object) -> Optional[Anime]:
    if isinstance(item, Anime):
        return item
    if hasattr(item, "to_common"):
        try:
            common = item.to_common()
        except Exception:
            return None
        if isinstance(common, Anime):
            return common
    return None


def _normalise_title_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lowered = value.casefold().replace("&", " and ").replace("\u00d7", " x ")
    collapsed = _TITLE_KEY_RE.sub(" ", lowered).strip()
    return " ".join(collapsed.split()) or None


def _title_key_variants(value: Optional[str]) -> List[str]:
    candidates = []
    if value:
        normalised = unicodedata.normalize("NFKC", value)
        jaconv_normalised = jaconv.normalize(value)
        kana_candidates = [
            jaconv.kata2hira(normalised),
            jaconv.hira2kata(normalised),
            jaconv.kata2hira(jaconv_normalised),
            jaconv.hira2kata(jaconv_normalised),
        ]
        candidates.extend([value, normalised, jaconv_normalised, *kana_candidates])
        for candidate in list(candidates):
            candidates.append(anyascii(candidate))
            candidates.append(unidecode(candidate))

    keys = []
    for candidate in candidates:
        key = _normalise_title_key(candidate)
        if key and key not in keys:
            keys.append(key)
    return keys


def _anime_title_keys(anime: Anime) -> List[str]:
    raw = [anime.title.romaji, anime.title.english, anime.title.native, *list(anime.title_synonyms or [])]
    keys = []
    for value in raw:
        for key in _title_key_variants(value):
            if key not in keys:
                keys.append(key)
    return keys


def _is_strong_title_key(key: str) -> bool:
    compact = key.replace(" ", "")
    return len(compact) >= 3 and compact not in _WEAK_TITLE_KEYS


def _title_key_by_role(anime: Anime) -> Dict[str, List[str]]:
    roles = {
        "romaji": [anime.title.romaji],
        "english": [anime.title.english],
        "native": [anime.title.native],
        "synonym": list(anime.title_synonyms or []),
    }
    out = {}
    for role, values in roles.items():
        keys = []
        for value in values:
            for key in _title_key_variants(value):
                if key not in keys:
                    keys.append(key)
        out[role] = keys
    return out


def _shared_external_id(left: Anime, right: Anime) -> bool:
    for key, value in (left.ids or {}).items():
        if value and (right.ids or {}).get(key) == value:
            return True
    return False


def _title_match_score(left: Anime, right: Anime) -> int:
    left_roles = _title_key_by_role(left)
    right_roles = _title_key_by_role(right)
    left_all = set().union(*left_roles.values()) if left_roles else set()
    right_all = set().union(*right_roles.values()) if right_roles else set()
    overlap = {key for key in left_all & right_all if _is_strong_title_key(key)}
    score = 0
    if overlap:
        score = max(score, 45)
    if {key for key in set(left_roles["romaji"]) & set(right_roles["romaji"]) if _is_strong_title_key(key)}:
        score = max(score, 55)
    if {key for key in set(left_roles["english"]) & set(right_roles["english"]) if _is_strong_title_key(key)}:
        score = max(score, 50)
    if {key for key in set(left_roles["native"]) & set(right_roles["native"]) if _is_strong_title_key(key)}:
        score = max(score, 50)
    synonym_overlap = (set(left_roles["synonym"]) & right_all) | (set(right_roles["synonym"]) & left_all)
    if {key for key in synonym_overlap if _is_strong_title_key(key)}:
        score = max(score, 35)

    comparable = [
        (left.title.romaji, right.title.romaji),
        (left.title.english, right.title.english),
        (left.title.romaji, right.title.english),
        (left.title.english, right.title.romaji),
    ]
    for left_value, right_value in comparable:
        left_key = _normalise_title_key(left_value)
        right_key = _normalise_title_key(right_value)
        if not left_key or not right_key:
            continue
        ratio = SequenceMatcher(None, left_key, right_key).ratio()
        if ratio >= 0.96:
            score = max(score, 45)
        elif ratio >= 0.92:
            score = max(score, 35)
    return score


def _context_match_score(left: Anime, right: Anime) -> int:
    score = 0
    if left.season_year is not None and right.season_year is not None:
        score += 15 if left.season_year == right.season_year else -35
    if left.season is not None and right.season is not None:
        score += 10 if left.season == right.season else -20
    if left.format is not None and right.format is not None:
        score += 6 if left.format == right.format else -10
    if left.episodes is not None and right.episodes is not None:
        if left.episodes == right.episodes:
            score += 6
        elif abs(left.episodes - right.episodes) > 2:
            score -= 4
    if left.aired_from is not None and right.aired_from is not None:
        delta = abs((left.aired_from - right.aired_from).days)
        if delta <= 14:
            score += 8
        elif delta > 90:
            score -= 8
    return score


def _anime_match_score(left: Anime, right: Anime) -> int:
    if _shared_external_id(left, right):
        return 1000
    title_score = _title_match_score(left, right)
    if title_score < 35:
        return 0
    score = title_score + _context_match_score(left, right)
    return score if score >= _MERGE_THRESHOLD else 0


def _choose_merged_title(records: Dict[str, Anime]) -> AnimeTitle:
    ordered = [records[name] for name in ("anilist", "jikan") if name in records]
    ordered.extend(record for backend, record in records.items() if backend not in ("anilist", "jikan"))
    primary = ordered[0]
    english = primary.title.english
    native = primary.title.native
    for record in ordered[1:]:
        english = english or record.title.english
        native = native or record.title.native
    return AnimeTitle(romaji=primary.title.romaji, english=english, native=native)


def _merge_group(records: Dict[str, Anime]) -> MergedAnime:
    ids = {}
    sources = []
    for backend, record in records.items():
        for key, value in (record.ids or {}).items():
            ids.setdefault(key, value)
        sources.append(record.source)
        if ":" in record.id:
            source_name, source_id = record.id.split(":", 1)
            ids.setdefault(source_name, source_id)
        else:
            ids.setdefault(backend, record.id)
    return MergedAnime(title=_choose_merged_title(records), ids=ids, sources=sources, records=records)


def _merge_season_items(result: AggregateResult) -> AggregateResult:
    groups: List[Dict[str, Anime]] = []
    passthrough = []

    for item in result.items:
        anime = _to_common_anime(item)
        if anime is None:
            passthrough.append(item)
            continue
        backend = anime.source.backend
        best_group = None
        best_score = 0
        for idx, group in enumerate(groups):
            if backend in group:
                continue
            score = max((_anime_match_score(anime, candidate) for candidate in group.values()), default=0)
            if score > best_score:
                best_group = idx
                best_score = score
        if best_group is None or best_score <= 0:
            best_group = len(groups)
            groups.append({})
        groups[best_group][backend] = anime

    merged = [_merge_group(group) for group in groups]
    return result.model_copy(update={"items": [*merged, *passthrough]})


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

    return _merge_season_items(_source_fanout(selected, _factory))


def schedule(
    *,
    day: str = "all",
    source: str = "all",
    limit: int = 25,
    timezone_name: Optional[str] = None,
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
    :param timezone_name: Display/query timezone. Defaults to local.
    :type timezone_name: str or None
    :param config: Optional runtime config.
    :type config: Config or None
    :return: Aggregate envelope.
    :rtype: ScheduleCalendarResult
    """
    if limit < 1:
        raise ApiError("--limit must be >= 1", backend="aggregate", reason="bad-args")
    resolved_day = _normalise_day(day)
    selected = _select_sources(source)
    target_tz, tz_label = _resolve_timezone(timezone_name)
    today = _now_local().astimezone(target_tz).date()
    start, end = _date_window(resolved_day, today=today)
    lower, upper = _epoch_window(start, end, target_tz)
    jikan_filters = _jikan_filters_for_day(resolved_day, today=today)

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
            rows = []
            seen = set()
            source_tag = None
            for jikan_filter in jikan_filters:
                response = _jikan.schedules(filter=jikan_filter, limit=limit, config=config, **kw)
                source_tag = response.source_tag
                for row in _jikan_schedule_rows(response, start=start, target_tz=target_tz):
                    key = (row.title, row.airing_at, row.weekday, row.local_time)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)
            if source_tag is None:
                return []
            return rows

        return FanoutSource("jikan", _jikan_rows)

    filtered_result = _filter_schedule_window(_source_fanout(selected, _factory), start=start, end=end, tz=target_tz)
    sorted_result = _sort_schedule_items(filtered_result, start=start, tz=target_tz)
    return ScheduleCalendarResult(
        items=sorted_result.items,
        sources=sorted_result.sources,
        timezone=tz_label,
        window_start=start,
        window_end=end,
    )


def selftest() -> bool:
    """Smoke-test calendar helpers and title transliteration dependencies.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert current_anime_season(date(2026, 1, 1)) == "winter"
    assert current_anime_season(date(2026, 4, 1)) == "spring"
    assert current_anime_season(date(2026, 7, 1)) == "summer"
    assert current_anime_season(date(2026, 10, 1)) == "fall"
    assert _select_sources("jikan,anilist,jikan") == ("jikan", "anilist")
    assert _normalise_day("Today") == "today"
    assert _jikan_filters_for_day("monday", today=date(2026, 5, 11)) == ("sunday", "monday", "tuesday")
    assert _resolve_timezone("UTC")[1] == "UTC"
    assert _resolve_timezone("+08:00")[1] == "+08:00"
    assert "pokemon" in _title_key_variants("Pok\u00e9mon")
    return True
