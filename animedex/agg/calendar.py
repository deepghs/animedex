"""Calendar aggregate commands over AniList and Jikan.

This module composes the existing high-level backend APIs into
multi-source calendar results. It owns only selection, date/season
inference, and per-source fan-out; backend-specific request logic
stays under :mod:`animedex.backends`.
"""

from __future__ import annotations

import re
import unicodedata
import logging
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

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
from animedex.utils.timezone import now_local, parse_timezone


SEASONS: Tuple[str, ...] = ("winter", "spring", "summer", "fall")
SOURCES: Tuple[str, ...] = ("anilist", "jikan")
WEEKDAYS: Tuple[str, ...] = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAYS: Tuple[str, ...] = (*WEEKDAYS, "today", "tomorrow", "all")
_TITLE_KEY_RE = re.compile(r"[^0-9a-z]+")
# Calibration notes:
# - _MERGE_THRESHOLD is the cumulative score at which a candidate pair is treated as the same anime. It is tuned
#   against the 2010-2025 adjudicated baseline at test/fixtures/aggregate/season_matrix/expected_matches.json with
#   a target of at least 95% recall on confirmed cross-source pairs while keeping precision at least 99% on confirmed
#   distinct pairs. Lowering the value increases recall and decreases precision; the rule is biased toward precision
#   because a wrong merge misleads the caller about which upstream said what.
# - SequenceMatcher ratio cutoffs of 0.96 and 0.92 are tuned against the same corpus; they add to the title score but
#   are still gated by _MERGE_THRESHOLD, so they cannot cause a merge on their own.
# Re-run tools/merge_eval/evaluate_rule.py after any threshold change.
_MERGE_THRESHOLD = 70
_WEAK_TITLE_KEYS = frozenset({"x", "ii", "iii", "iv", "v"})
_TOKYO_TZ_ALIASES = frozenset({"asia/tokyo", "jst", "utc+9", "utc+09:00"})
_LOGGER = logging.getLogger(__name__)


def _now_local() -> datetime:
    return now_local()


def _jikan_source_timezone(name: Optional[str], *, target_tz: Optional[tzinfo] = None) -> Optional[tzinfo]:
    if not isinstance(name, str):
        return target_tz
    normalized = name.strip().lower()
    if not normalized:
        return target_tz
    if normalized in _TOKYO_TZ_ALIASES:
        try:
            return parse_timezone("Asia/Tokyo").tzinfo
        except ValueError:
            return timezone(timedelta(hours=9), name="JST")
    try:
        return parse_timezone(name).tzinfo
    except ValueError:
        return target_tz


def _resolve_timezone(value: Optional[str]) -> Tuple[tzinfo, str]:
    try:
        resolved = parse_timezone(value, local_now=_now_local())
    except ValueError as exc:
        raise ApiError(
            f"unknown timezone: {value!r}; expected local, UTC, an IANA name, a dateutil TZ string, or an offset like +08:00",
            backend="aggregate",
            reason="bad-args",
        ) from exc
    return resolved.tzinfo, resolved.label


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


def _compact_dict(values: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            continue
        out[key] = value
    return out


def _model_payload(value: object) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return dict(value)
    return {}


def _append_unique(values: List[Any], value: Any) -> None:
    if value is not None and value != "" and value not in values:
        values.append(value)


def _entity_names(values: object) -> List[str]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
        return []
    names = []
    for value in values:
        name = getattr(value, "name", None)
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


def _nested_image_url(row: object) -> Optional[str]:
    images = getattr(row, "images", None)
    jpg = getattr(images, "jpg", None) if images is not None else None
    return getattr(jpg, "large_image_url", None) or getattr(jpg, "image_url", None)


def _contains_range(text: str, ranges: Sequence[Tuple[int, int]]) -> bool:
    return any(start <= ord(char) <= end for char in text for start, end in ranges)


_KANA_RANGES = ((0x3040, 0x30FF), (0x31F0, 0x31FF))
_HAN_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x2FA1F))
_HANGUL_RANGES = ((0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7AF), (0xD7B0, 0xD7FF))


def _classify_title_scripts(title: str) -> List[str]:
    scripts = []
    if _contains_range(title, _KANA_RANGES):
        scripts.append("kana")
    if _contains_range(title, _HAN_RANGES):
        scripts.append("han")
    if _contains_range(title, _HANGUL_RANGES):
        scripts.append("hangul")
    return scripts


def _language_from_title_type(title_type: Optional[str]) -> Optional[str]:
    value = (title_type or "").strip().casefold()
    if not value:
        return None
    if value in ("english", "en"):
        return "english"
    if value in ("japanese", "ja", "native"):
        return "japanese"
    if value in ("chinese", "mandarin", "zh"):
        return "chinese"
    if value in ("korean", "ko"):
        return "korean"
    return None


def _add_title_variant(
    variants: Dict[str, Any],
    title: Optional[str],
    *,
    kind: Optional[str] = None,
    language: Optional[str] = None,
) -> None:
    if not isinstance(title, str) or not title.strip():
        return
    text = title.strip()
    _append_unique(variants["all"], text)
    if kind:
        typed = {"type": kind, "title": text}
        if typed not in variants["typed"]:
            variants["typed"].append(typed)
    if language:
        _append_unique(variants["by_language"].setdefault(language, []), text)
    for script in _classify_title_scripts(text):
        _append_unique(variants["by_script"].setdefault(script, []), text)
        if script == "kana":
            _append_unique(variants["by_language"].setdefault("japanese", []), text)
        elif script == "han" and language is None and "kana" not in _classify_title_scripts(text):
            _append_unique(variants["by_language"].setdefault("chinese", []), text)
        elif script == "hangul":
            _append_unique(variants["by_language"].setdefault("korean", []), text)


def _title_variants_from_parts(
    primary: Optional[str],
    *,
    english: Optional[str] = None,
    native: Optional[str] = None,
    synonyms: Sequence[str] = (),
    raw: object = None,
) -> Dict[str, Any]:
    variants: Dict[str, Any] = {
        "primary": primary,
        "romaji": primary,
        "english": english,
        "native": native,
        "synonyms": [],
        "typed": [],
        "all": [],
        "by_language": {},
        "by_script": {},
    }
    _add_title_variant(variants, primary, kind="romaji")
    _add_title_variant(variants, english, kind="english", language="english")
    _add_title_variant(variants, native, kind="native", language="japanese")
    for synonym in synonyms or []:
        _append_unique(variants["synonyms"], synonym)
        _add_title_variant(variants, synonym, kind="synonym")

    rich_title = getattr(raw, "title", None)
    for field, language in (("romaji", None), ("english", "english"), ("native", None)):
        _add_title_variant(variants, getattr(rich_title, field, None), kind=field, language=language)

    for entry in getattr(raw, "titles", None) or []:
        title_type = getattr(entry, "type", None)
        _add_title_variant(
            variants,
            getattr(entry, "title", None),
            kind=title_type,
            language=_language_from_title_type(title_type),
        )

    for field, title_type, language in (
        ("title", "Default", None),
        ("title_english", "English", "english"),
        ("title_japanese", "Japanese", "japanese"),
    ):
        _add_title_variant(variants, getattr(raw, field, None), kind=title_type, language=language)
    for synonym in getattr(raw, "title_synonyms", None) or []:
        _append_unique(variants["synonyms"], synonym)
        _add_title_variant(variants, synonym, kind="Synonym")

    variants["by_language"] = {language: titles for language, titles in variants["by_language"].items() if titles}
    variants["by_script"] = {script: titles for script, titles in variants["by_script"].items() if titles}
    return _compact_dict(variants)


def _title_variants(record: Anime, raw: object = None) -> Dict[str, Any]:
    return _title_variants_from_parts(
        record.title.romaji,
        english=record.title.english,
        native=record.title.native,
        synonyms=record.title_synonyms or [],
        raw=raw,
    )


def _raw_tag_details(raw: object) -> List[Dict[str, Any]]:
    details = []
    for tag in getattr(raw, "tags", None) or []:
        name = getattr(tag, "name", None)
        if not name:
            continue
        detail = _compact_dict({"name": name, "rank": getattr(tag, "rank", None)})
        if detail not in details:
            details.append(detail)
    return details


def _raw_studio_names(raw: object) -> List[str]:
    direct = _entity_names(getattr(raw, "studios", None))
    if direct:
        return direct
    connection = getattr(raw, "studios", None)
    names = []
    for edge in getattr(connection, "edges", None) or []:
        node = getattr(edge, "node", None)
        name = getattr(node, "name", None)
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


def _broadcast_detail(raw: object) -> Optional[Dict[str, Any]]:
    broadcast = getattr(raw, "broadcast", None)
    if broadcast is None:
        return None
    return _compact_dict(
        {
            "day": getattr(broadcast, "day", None),
            "time": getattr(broadcast, "time", None),
            "timezone": getattr(broadcast, "timezone", None),
            "string": getattr(broadcast, "string", None),
        }
    )


def _anime_type_tags(record: Anime, raw: object = None) -> List[str]:
    tags = []
    for value in (
        record.format,
        record.status,
        record.season,
        record.source_material,
        record.age_rating,
        getattr(raw, "type", None),
        getattr(raw, "source", None),
        getattr(raw, "rating", None),
    ):
        _append_unique(tags, value)
    for values in (
        record.genres,
        record.tags,
        _entity_names(getattr(raw, "genres", None)),
        _entity_names(getattr(raw, "explicit_genres", None)),
        _entity_names(getattr(raw, "themes", None)),
        _entity_names(getattr(raw, "demographics", None)),
    ):
        for value in values or []:
            _append_unique(tags, value)
    if record.is_adult:
        _append_unique(tags, "adult")
    return tags


def _jikan_row_type_tags(row: object) -> List[str]:
    tags = []
    for value in (
        getattr(row, "type", None),
        getattr(row, "status", None),
        getattr(row, "source", None),
        getattr(row, "rating", None),
        getattr(row, "season", None),
    ):
        _append_unique(tags, value)
    for values in (
        _entity_names(getattr(row, "genres", None)),
        _entity_names(getattr(row, "explicit_genres", None)),
        _entity_names(getattr(row, "themes", None)),
        _entity_names(getattr(row, "demographics", None)),
    ):
        for value in values:
            _append_unique(tags, value)
    return tags


def _jikan_schedule_details(row: object, broadcast: object) -> Dict[str, Any]:
    broadcast = broadcast if isinstance(broadcast, dict) else {}
    return _compact_dict(
        {
            "backend": "jikan",
            "mal_id": getattr(row, "mal_id", None),
            "url": getattr(row, "url", None),
            "titles": _title_variants_from_parts(
                getattr(row, "title", None) or getattr(row, "name", None) or "Untitled",
                english=getattr(row, "title_english", None),
                native=getattr(row, "title_japanese", None),
                synonyms=list(getattr(row, "title_synonyms", None) or []),
                raw=row,
            ),
            "type": getattr(row, "type", None),
            "status": getattr(row, "status", None),
            "episodes": getattr(row, "episodes", None),
            "source_material": getattr(row, "source", None),
            "duration": getattr(row, "duration", None),
            "rating": getattr(row, "rating", None),
            "score": getattr(row, "score", None),
            "scored_by": getattr(row, "scored_by", None),
            "rank": getattr(row, "rank", None),
            "popularity": getattr(row, "popularity", None),
            "members": getattr(row, "members", None),
            "favorites": getattr(row, "favorites", None),
            "broadcast_day": broadcast.get("day"),
            "broadcast_time": broadcast.get("time"),
            "broadcast_timezone": broadcast.get("timezone"),
            "broadcast_string": broadcast.get("string"),
            "studios": _entity_names(getattr(row, "studios", None)),
            "genres": _entity_names(getattr(row, "genres", None)),
            "themes": _entity_names(getattr(row, "themes", None)),
            "demographics": _entity_names(getattr(row, "demographics", None)),
            "type_tags": _jikan_row_type_tags(row),
            "image_url": _nested_image_url(row),
        }
    )


def _source_tag_summary(source: SourceTag) -> Dict[str, Any]:
    return _compact_dict(
        {
            "backend": source.backend,
            "fetched_at": source.fetched_at,
            "cached": source.cached,
            "rate_limited": source.rate_limited,
        }
    )


def _schedule_core(
    *,
    title: str,
    source: SourceTag,
    airing_at: Optional[datetime] = None,
    episode: Optional[int] = None,
    weekday: Optional[str] = None,
    local_time: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    details = details or {}
    return _compact_dict(
        {
            "title": title,
            "airing_at": airing_at,
            "episode": episode,
            "weekday": weekday,
            "local_time": local_time,
            "source": _source_tag_summary(source),
            "titles": details.get("titles"),
            "type_tags": details.get("type_tags"),
            "score": details.get("score"),
            "status": details.get("status"),
            "source_material": details.get("source_material"),
            "rating": details.get("rating"),
            "genres": details.get("genres"),
            "themes": details.get("themes"),
            "studios": details.get("studios"),
        }
    )


def _media_studio_names(media: Dict[str, Any]) -> List[str]:
    studios = media.get("studios")
    names = []
    if isinstance(studios, dict):
        for edge in studios.get("edges") or []:
            node = edge.get("node") if isinstance(edge, dict) else None
            name = node.get("name") if isinstance(node, dict) else None
            if isinstance(name, str):
                _append_unique(names, name)
    return names


def _anilist_media_type_tags(media: Dict[str, Any]) -> List[str]:
    tags = []
    for value in (
        media.get("type"),
        media.get("format"),
        media.get("status"),
        media.get("season"),
        media.get("source"),
    ):
        _append_unique(tags, value)
    for value in media.get("genres") or []:
        _append_unique(tags, value)
    for tag in media.get("tags") or []:
        if isinstance(tag, dict):
            _append_unique(tags, tag.get("name"))
    if media.get("isAdult"):
        _append_unique(tags, "adult")
    return tags


def _anilist_schedule_details_from_payload(payload: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
    media = payload.get("media") if isinstance(payload, dict) else None
    if not isinstance(media, dict):
        return details
    title = media.get("title") if isinstance(media.get("title"), dict) else {}
    enriched = dict(details)
    enriched.update(
        _compact_dict(
            {
                "titles": _title_variants_from_parts(
                    title.get("romaji") or title.get("english") or title.get("native") or "Untitled",
                    english=title.get("english"),
                    native=title.get("native"),
                    synonyms=list(media.get("synonyms") or []),
                ),
                "mal_id": media.get("idMal"),
                "type": media.get("type"),
                "format": media.get("format"),
                "status": media.get("status"),
                "episodes": media.get("episodes"),
                "source_material": media.get("source"),
                "duration": media.get("duration"),
                "score": media.get("averageScore"),
                "mean_score": media.get("meanScore"),
                "popularity": media.get("popularity"),
                "favorites": media.get("favourites"),
                "trending": media.get("trending"),
                "season": media.get("season"),
                "season_year": media.get("seasonYear"),
                "studios": _media_studio_names(media),
                "genres": list(media.get("genres") or []),
                "tags": [
                    tag.get("name") for tag in media.get("tags") or [] if isinstance(tag, dict) and tag.get("name")
                ],
                "tag_details": [
                    _compact_dict({"name": tag.get("name"), "rank": tag.get("rank")})
                    for tag in media.get("tags") or []
                    if isinstance(tag, dict) and tag.get("name")
                ],
                "type_tags": _anilist_media_type_tags(media),
                "country_of_origin": media.get("countryOfOrigin"),
                "is_adult": media.get("isAdult"),
                "cover_image": media.get("coverImage"),
                "banner_image": media.get("bannerImage"),
                "trailer": media.get("trailer"),
                "next_airing_episode": media.get("nextAiringEpisode"),
            }
        )
    )
    return enriched


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
    details = {}
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
        details = _jikan_schedule_details(row, broadcast)
    return AiringScheduleRow(
        title=title,
        airing_at=airing_at,
        weekday=weekday,
        local_time=local_time,
        source=source_tag,
        core=_schedule_core(
            title=title,
            source=source_tag,
            airing_at=airing_at,
            weekday=weekday,
            local_time=local_time,
            details=details,
        ),
        details=details,
        source_payload=_model_payload(row),
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


def _to_common_schedule_row(item: object) -> Optional[AiringScheduleRow]:
    if isinstance(item, AiringScheduleRow):
        return item
    if hasattr(item, "to_common"):
        try:
            common = item.to_common()
        except Exception:
            return None
        if isinstance(common, AiringScheduleRow):
            return common
    return None


def _project_schedule_items(result: AggregateResult, *, target_tz: tzinfo) -> AggregateResult:
    items = []
    for item in result.items:
        row = _to_common_schedule_row(item)
        if row is None:
            items.append(item)
            continue
        update = {}
        if row.airing_at is not None:
            update["airing_at"] = row.airing_at.astimezone(target_tz)
        details = row.details
        if row.source.backend == "anilist":
            details = _anilist_schedule_details_from_payload(row.source_payload, row.details)
            if details != row.details:
                update["details"] = details
        if not row.core or details != row.details:
            update["core"] = _schedule_core(
                title=row.title,
                source=row.source,
                airing_at=update.get("airing_at", row.airing_at),
                episode=row.episode,
                weekday=row.weekday,
                local_time=row.local_time,
                details=details,
            )
        if not row.source_payload:
            update["source_payload"] = _model_payload(item)
        if update:
            row = row.model_copy(update=update)
        items.append(row)
    return result.model_copy(update={"items": items})


def _to_common_anime(item: object) -> Optional[Anime]:
    anime, _diagnostic = _to_common_anime_with_diagnostic(item)
    return anime


def _merge_diagnostic_identity(item: object) -> Dict[str, Any]:
    source_tag = getattr(item, "source_tag", None) or getattr(item, "source", None)
    backend = getattr(source_tag, "backend", None) or getattr(item, "backend", None)
    ident = getattr(item, "id", None) or getattr(item, "mal_id", None) or getattr(item, "media_id", None)
    return _compact_dict({"backend": backend, "id": str(ident) if ident is not None else None})


def _to_common_anime_with_diagnostic(item: object) -> Tuple[Optional[Anime], Optional[Dict[str, Any]]]:
    if isinstance(item, Anime):
        return item, None
    if hasattr(item, "to_common"):
        try:
            common = item.to_common()
        except (ValueError, AttributeError, KeyError) as exc:
            identity = _merge_diagnostic_identity(item)
            diagnostic = {
                **identity,
                "reason": "to-common-failed",
                "message": f"{type(exc).__name__}: {exc}",
            }
            _LOGGER.debug(
                "Skipping aggregate season merge candidate after to_common() failed: %s",
                diagnostic,
                exc_info=True,
            )
            return None, diagnostic
        if isinstance(common, Anime):
            return common, None
    return None, None


def _normalise_title_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lowered = value.casefold().replace("&", " and ").replace("\u00d7", " x ")
    collapsed = _TITLE_KEY_RE.sub(" ", lowered).strip()
    return " ".join(collapsed.split()) or None


def _title_key_variants(value: Optional[str]) -> List[str]:
    """Return normalised title keys across kana, width, and ASCII variants.

    ``jaconv`` handles Japanese kana and NFKC-style width differences that the generic transliterators do not cover.
    ``anyascii`` and ``unidecode`` are intentionally both used because they disagree on CJK/Hangul segmentation and
    romanisation details: for example ``怪獣８号`` becomes compact ``GuaiShou8Hao`` via ``anyascii`` but spaced
    ``Guai Swu 8Hao`` via ``unidecode``, while Hangul titles such as ``마녀와 야수`` produce different word-boundary
    candidates. Keeping both variants increases recall before the calibrated context score decides whether to merge.
    """
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


def _external_id_conflicts(left: Anime, right: Anime) -> List[Dict[str, str]]:
    conflicts = []
    left_ids = left.ids or {}
    right_ids = right.ids or {}
    for key in sorted(set(left_ids) & set(right_ids)):
        left_value = left_ids.get(key)
        right_value = right_ids.get(key)
        if left_value is None or right_value is None:
            continue
        left_text = str(left_value)
        right_text = str(right_value)
        if left_text and right_text and left_text != right_text:
            conflicts.append(
                {
                    "key": str(key),
                    "left_backend": left.source.backend,
                    "left_value": left_text,
                    "right_backend": right.source.backend,
                    "right_value": right_text,
                }
            )
    return conflicts


def _has_external_id_conflict(left: Anime, right: Anime) -> bool:
    return bool(_external_id_conflicts(left, right))


def _group_has_external_id_conflict(candidate: Anime, group: Dict[str, Anime]) -> bool:
    return any(_has_external_id_conflict(candidate, record) for record in group.values())


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
    if _has_external_id_conflict(left, right):
        return 0
    if _shared_external_id(left, right):
        return 1000
    title_score = _title_match_score(left, right)
    if title_score < 35:
        return 0
    score = title_score + _context_match_score(left, right)
    return score if score >= _MERGE_THRESHOLD else 0


def _choose_merged_title(records: Dict[str, Anime]) -> AnimeTitle:
    """Choose the merged row's compact display title.

    AniList is preferred, then Jikan, because AniList's romaji/native/English title block is the most consistent title
    schema across the 2010-2025 season corpus. Secondary sources still fill missing English/native slots, and every
    source's full title set remains available under ``records`` and ``source_details`` for JSON consumers.
    """
    ordered = [records[name] for name in ("anilist", "jikan") if name in records]
    ordered.extend(record for backend, record in records.items() if backend not in ("anilist", "jikan"))
    primary = ordered[0]
    english = primary.title.english
    native = primary.title.native
    for record in ordered[1:]:
        english = english or record.title.english
        native = native or record.title.native
    return AnimeTitle(romaji=primary.title.romaji, english=english, native=native)


def _score_detail(anime: Anime) -> Optional[Dict[str, Any]]:
    if anime.score is None:
        return None
    return _compact_dict({"score": anime.score.score, "scale": anime.score.scale, "votes": anime.score.votes})


def _next_airing_detail(anime: Anime) -> Optional[Dict[str, Any]]:
    if anime.next_airing_episode is None:
        return None
    next_ep = anime.next_airing_episode
    return {
        "episode": next_ep.episode,
        "airing_at": next_ep.airing_at,
        "time_until_airing_seconds": next_ep.time_until_airing_seconds,
    }


def _merged_title_details(title: AnimeTitle, source_details: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    merged = _title_variants_from_parts(title.romaji, english=title.english, native=title.native)
    merged.setdefault("synonyms", [])
    merged.setdefault("typed", [])
    merged.setdefault("all", [])
    merged.setdefault("by_language", {})
    merged.setdefault("by_script", {})
    for details in source_details.values():
        titles = details.get("titles")
        if not isinstance(titles, dict):
            continue
        for field in ("primary", "romaji", "english", "native"):
            _add_title_variant(merged, titles.get(field), kind=field)
        for synonym in titles.get("synonyms") or []:
            _append_unique(merged.setdefault("synonyms", []), synonym)
            _add_title_variant(merged, synonym, kind="synonym")
        typed = titles.get("typed")
        if isinstance(typed, list):
            for entry in typed:
                if not isinstance(entry, dict):
                    continue
                _add_title_variant(
                    merged,
                    entry.get("title"),
                    kind=entry.get("type"),
                    language=_language_from_title_type(entry.get("type")),
                )
        by_language = titles.get("by_language")
        if isinstance(by_language, dict):
            for language, values in by_language.items():
                for value in values or []:
                    _add_title_variant(merged, value, language=language)
    return _compact_dict(merged)


def _score_summary(source_details: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    scores = {}
    normalised = {}
    for backend, details in source_details.items():
        score = details.get("score")
        if not isinstance(score, dict) or score.get("score") is None:
            continue
        scores[backend] = score
        scale = score.get("scale")
        if scale:
            normalised[backend] = float(score["score"]) / float(scale) * 100.0
    return _compact_dict({"by_source": scores, "normalised_100": normalised})


def _collect_unique_field(
    source_details: Dict[str, Dict[str, Any]], field: str, *, limit: Optional[int] = None
) -> List[Any]:
    out = []
    for details in source_details.values():
        values = details.get(field)
        if not isinstance(values, list):
            values = [values] if values is not None else []
        for value in values:
            _append_unique(out, value)
            if limit is not None and len(out) >= limit:
                return out
    return out


def _merged_airing_summary(records: Dict[str, Anime], source_details: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    primary = next(iter(records.values())) if records else None
    by_source = {}
    for backend, details in source_details.items():
        by_source[backend] = _compact_dict(
            {
                "season": details.get("season"),
                "season_year": details.get("season_year"),
                "aired_from": details.get("aired_from"),
                "aired_to": details.get("aired_to"),
                "status": details.get("status"),
                "broadcast": details.get("broadcast"),
                "next_airing_episode": details.get("next_airing_episode"),
            }
        )
    return _compact_dict(
        {
            "season": primary.season if primary else None,
            "season_year": primary.season_year if primary else None,
            "aired_from": primary.aired_from if primary else None,
            "aired_to": primary.aired_to if primary else None,
            "status": primary.status if primary else None,
            "by_source": by_source,
        }
    )


def _merged_core(
    *,
    title: AnimeTitle,
    ids: Dict[str, str],
    sources: List[SourceTag],
    records: Dict[str, Anime],
    source_details: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    primary = next(iter(records.values())) if records else None
    return _compact_dict(
        {
            "title": title.model_dump(mode="json"),
            "titles": _merged_title_details(title, source_details),
            "ids": dict(ids),
            "sources": [_source_tag_summary(source) for source in sources],
            "format": primary.format if primary else None,
            "episodes": primary.episodes if primary else None,
            "airing": _merged_airing_summary(records, source_details),
            "scores": _score_summary(source_details),
            "studios": _collect_unique_field(source_details, "studios", limit=8),
            "genres": _collect_unique_field(source_details, "genres", limit=12),
            "tags": _collect_unique_field(source_details, "tags", limit=12),
            "type_tags": _collect_unique_field(source_details, "type_tags", limit=16),
            "source_material": primary.source_material if primary else None,
            "age_rating": primary.age_rating if primary else None,
            "country_of_origin": primary.country_of_origin if primary else None,
            "is_adult": primary.is_adult if primary else None,
        }
    )


def _anime_source_details(record: Anime, raw: object = None) -> Dict[str, Any]:
    raw = raw or record
    return _compact_dict(
        {
            "backend": record.source.backend,
            "id": record.id,
            "ids": dict(record.ids or {}),
            "title": record.title.romaji,
            "english_title": record.title.english,
            "native_title": record.title.native,
            "title_synonyms": list(record.title_synonyms or []),
            "titles": _title_variants(record, raw),
            "score": _score_detail(record),
            "mean_score": getattr(raw, "meanScore", None),
            "scored_by": getattr(raw, "scored_by", None),
            "rank": getattr(raw, "rank", None),
            "members": getattr(raw, "members", None),
            "format": record.format,
            "raw_type": getattr(raw, "type", None),
            "status": record.status,
            "raw_status": getattr(raw, "status", None),
            "airing": getattr(raw, "airing", None),
            "episodes": record.episodes,
            "season": record.season,
            "season_year": record.season_year,
            "aired_from": record.aired_from,
            "aired_to": record.aired_to,
            "duration_minutes": record.duration_minutes,
            "studios": list(record.studios or []) or _raw_studio_names(raw),
            "producers": _entity_names(getattr(raw, "producers", None)),
            "licensors": _entity_names(getattr(raw, "licensors", None)),
            "genres": list(record.genres or []),
            "tags": list(record.tags or []),
            "tag_details": _raw_tag_details(raw),
            "explicit_genres": _entity_names(getattr(raw, "explicit_genres", None)),
            "themes": _entity_names(getattr(raw, "themes", None)),
            "demographics": _entity_names(getattr(raw, "demographics", None)),
            "type_tags": _anime_type_tags(record, raw),
            "popularity": record.popularity,
            "favourites": record.favourites,
            "trending": record.trending,
            "age_rating": record.age_rating,
            "source_material": record.source_material,
            "country_of_origin": record.country_of_origin,
            "is_adult": record.is_adult,
            "cover_image_url": record.cover_image_url,
            "banner_image_url": record.banner_image_url,
            "trailer_url": record.trailer_url,
            "url": getattr(raw, "url", None),
            "broadcast": _broadcast_detail(raw),
            "next_airing_episode": _next_airing_detail(record),
        }
    )


def _merge_group(records: Dict[str, Anime], raw_records: Optional[Dict[str, object]] = None) -> MergedAnime:
    ids = {}
    id_conflicts = []
    sources = []
    source_details = {}
    source_payloads = {}
    raw_records = raw_records or {}

    def _set_id(key: str, value: object, *, backend: str, source: str) -> None:
        if value is None:
            return
        text = str(value)
        if not text:
            return
        if key in ids and str(ids[key]) != text:
            id_conflicts.append(
                {
                    "key": str(key),
                    "kept_value": str(ids[key]),
                    "conflicting_value": text,
                    "backend": backend,
                    "source": source,
                }
            )
            return
        ids.setdefault(key, text)

    for backend, record in records.items():
        raw = raw_records.get(backend, record)
        for key, value in (record.ids or {}).items():
            _set_id(key, value, backend=backend, source="record.ids")
        sources.append(record.source)
        source_details[backend] = _anime_source_details(record, raw)
        source_payloads[backend] = _model_payload(raw)
        if ":" in record.id:
            source_name, source_id = record.id.split(":", 1)
            _set_id(source_name, source_id, backend=backend, source="record.id")
        else:
            _set_id(backend, record.id, backend=backend, source="record.id")
    title = _choose_merged_title(records)
    core = _merged_core(title=title, ids=ids, sources=sources, records=records, source_details=source_details)
    if id_conflicts:
        core["id_conflicts"] = id_conflicts
    return MergedAnime(
        title=title,
        ids=ids,
        sources=sources,
        records=records,
        core=core,
        source_details=source_details,
        source_payloads=source_payloads,
        id_conflicts=id_conflicts,
    )


def _merge_season_items(result: AggregateResult) -> AggregateResult:
    groups: List[Dict[str, Anime]] = []
    raw_groups: List[Dict[str, object]] = []
    passthrough = []
    diagnostics = list(result.merge_diagnostics or [])

    for item in result.items:
        anime, diagnostic = _to_common_anime_with_diagnostic(item)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        if anime is None:
            passthrough.append(item)
            continue
        backend = anime.source.backend
        best_group = None
        best_score = 0
        for idx, group in enumerate(groups):
            if backend in group:
                continue
            if _group_has_external_id_conflict(anime, group):
                continue
            score = max((_anime_match_score(anime, candidate) for candidate in group.values()), default=0)
            if score > best_score:
                best_group = idx
                best_score = score
        if best_group is None or best_score <= 0:
            best_group = len(groups)
            groups.append({})
            raw_groups.append({})
        groups[best_group][backend] = anime
        raw_groups[best_group][backend] = item

    merged = []
    for idx, group in enumerate(groups):
        item = _merge_group(group, raw_groups[idx])
        merged.append(item)
        for conflict in item.id_conflicts:
            diagnostics.append(
                {
                    "backend": conflict.get("backend"),
                    "id": next(iter(item.records.values())).id if item.records else None,
                    "reason": "external-id-conflict",
                    "message": (
                        f"conflicting external id for {conflict.get('key')!r}: "
                        f"{conflict.get('kept_value')!r} != {conflict.get('conflicting_value')!r}"
                    ),
                    "conflicts": item.id_conflicts,
                }
            )
    return result.model_copy(update={"items": [*merged, *passthrough], "merge_diagnostics": diagnostics})


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

    projected_result = _project_schedule_items(_source_fanout(selected, _factory), target_tz=target_tz)
    filtered_result = _filter_schedule_window(projected_result, start=start, end=end, tz=target_tz)
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
    assert _resolve_timezone("UTC+8")[1] == "+08:00"
    assert _resolve_timezone("CST-8")[0].utcoffset(datetime(2026, 1, 1)).total_seconds() == 8 * 3600
    assert "pokemon" in _title_key_variants("Pok\u00e9mon")
    return True
