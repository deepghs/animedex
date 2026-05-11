"""
TTY renderer: human-friendly tables with explicit source markers.

The TTY path always shows the ``[src: <backend>]`` annotation per
``plans/03 §5`` because the human reader cannot inspect a JSON
``_source`` field. :func:`render_for_stream` is the auto-switching
entry point used by the CLI: it picks :func:`render_tty` when the
destination is a terminal and the JSON renderer otherwise so
piped output remains parseable.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from animedex.models.anime import AiringScheduleRow, Anime
from animedex.models.aggregate import AggregateResult, MergedAnime, ScheduleCalendarResult
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import AnimedexModel
from animedex.models.trace import TraceHit, TraceQuota
from animedex.render.json_renderer import render_json

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")


def is_terminal(stream: Any) -> bool:
    """Return ``True`` when ``stream`` is connected to a terminal.

    :param stream: Anything with an ``isatty`` method (typically
                    ``sys.stdout`` in production, a fake stream in
                    tests).
    :type stream: Any
    :return: ``True`` when the stream reports it is a TTY.
    :rtype: bool
    """
    return bool(getattr(stream, "isatty", lambda: False)())


def _truncate(text: Optional[str], n: int = 280) -> Optional[str]:
    """Trim multi-paragraph blobs (description / synopsis) so the TTY
    rendering stays scannable; ``--json`` always carries the full
    text."""
    if text is None:
        return None
    text = text.replace("\n\n", " · ").replace("\n", " ").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def _format_anime_tty(anime: Anime) -> str:
    src_marker = f"[src: {anime.source.backend}]"
    out = io.StringIO()

    # Header: full title block
    print(f"{anime.title.romaji}  {src_marker}", file=out)
    if anime.title.english and anime.title.english != anime.title.romaji:
        print(f"  English:  {anime.title.english}", file=out)
    if anime.title.native:
        print(f"  Native:   {anime.title.native}", file=out)
    if anime.title_synonyms:
        # Show up to 8 synonyms inline; everything else on continuation lines
        first_line = anime.title_synonyms[0]
        rest = anime.title_synonyms[1:]
        print(f"  Synonyms: {first_line}", file=out)
        for syn in rest[:7]:
            print(f"            {syn}", file=out)
        if len(rest) > 7:
            print(f"            (+{len(rest) - 7} more)", file=out)

    # Identity / ids
    id_bits = [anime.id]
    for src, val in (anime.ids or {}).items():
        if f"{src}:{val}" != anime.id:
            id_bits.append(f"{src}:{val}")
    print(f"  ID:       {' | '.join(id_bits)}", file=out)

    # Format / status / counts (single line)
    fmt_bits = []
    if anime.format:
        fmt_bits.append(anime.format)
    if anime.status:
        fmt_bits.append(anime.status)
    if anime.episodes is not None:
        fmt_bits.append(f"{anime.episodes} ep")
    if anime.duration_minutes:
        fmt_bits.append(f"{anime.duration_minutes} min/ep")
    if fmt_bits:
        print(f"  Format:   {'  ·  '.join(fmt_bits)}", file=out)

    # Season / aired
    season_bits = []
    if anime.season:
        season_bits.append(anime.season)
    if anime.season_year:
        season_bits.append(str(anime.season_year))
    if anime.aired_from:
        if anime.aired_to:
            season_bits.append(f"{anime.aired_from.isoformat()} → {anime.aired_to.isoformat()}")
        else:
            season_bits.append(f"{anime.aired_from.isoformat()} → ongoing")
    if season_bits:
        print(f"  Aired:    {'  ·  '.join(season_bits)}", file=out)

    # Score / popularity
    score_bits = []
    if anime.score is not None:
        score_bits.append(f"{anime.score.score}/{anime.score.scale}")
        if anime.score.votes:
            score_bits.append(f"{anime.score.votes:,} votes")
    if anime.popularity is not None:
        score_bits.append(f"#{anime.popularity:,} popular")
    if anime.favourites is not None:
        score_bits.append(f"{anime.favourites:,} fav")
    if anime.trending is not None:
        score_bits.append(f"#{anime.trending} trending")
    if score_bits:
        print(f"  Score:    {'  ·  '.join(score_bits)}", file=out)

    # Studios / source / origin
    if anime.studios:
        print(f"  Studios:  {', '.join(anime.studios)}", file=out)
    misc = []
    if anime.source_material:
        misc.append(f"Source: {anime.source_material}")
    if anime.country_of_origin:
        misc.append(f"Origin: {anime.country_of_origin}")
    if anime.age_rating:
        misc.append(f"Rating: {anime.age_rating}")
    if anime.is_adult:
        misc.append("18+")
    if misc:
        print(f"  Origin:   {'  ·  '.join(misc)}", file=out)

    # Genres / tags
    if anime.genres:
        print(f"  Genres:   {', '.join(anime.genres)}", file=out)
    if anime.tags:
        tag_show = anime.tags[:8]
        more = f" (+{len(anime.tags) - 8} more)" if len(anime.tags) > 8 else ""
        print(f"  Tags:     {', '.join(tag_show)}{more}", file=out)

    # Next airing (when applicable)
    if anime.next_airing_episode:
        n = anime.next_airing_episode
        print(
            f"  Next ep:  ep {n.episode} airing {n.airing_at.isoformat()} (in {n.time_until_airing_seconds}s)",
            file=out,
        )

    # Streaming
    if anime.streaming:
        providers = [f"{link.provider}: {link.url}" for link in anime.streaming[:6]]
        print(f"  Streaming:{' ' + providers[0]}", file=out)
        for p in providers[1:]:
            print(f"            {p}", file=out)
        if len(anime.streaming) > 6:
            print(f"            (+{len(anime.streaming) - 6} more)", file=out)

    # Cover / banner / trailer URLs
    media = []
    if anime.cover_image_url:
        media.append(f"Cover: {anime.cover_image_url}")
    if anime.banner_image_url:
        media.append(f"Banner: {anime.banner_image_url}")
    if anime.trailer_url:
        media.append(f"Trailer: {anime.trailer_url}")
    for m in media:
        print(f"  {m}", file=out)

    # Synopsis (last; longest)
    if anime.description:
        print(f"  Synopsis: {_truncate(anime.description, 480)}", file=out)

    return out.getvalue()


def _format_character_tty(c: Character) -> str:
    src = f"[src: {c.source.backend}]"
    out = io.StringIO()
    print(f"{c.name}  {src}", file=out)
    if c.name_native:
        print(f"  Native:    {c.name_native}", file=out)
    if c.name_alternatives:
        print(f"  Alt names: {', '.join(c.name_alternatives)}", file=out)
    print(f"  ID:        {c.id}", file=out)
    bio = []
    if c.role:
        bio.append(f"Role: {c.role}")
    if c.gender:
        bio.append(f"Gender: {c.gender}")
    if c.age:
        bio.append(f"Age: {c.age}")
    if c.favourites is not None:
        bio.append(f"Favourites: {c.favourites:,}")
    if bio:
        print(f"  Profile:   {'  ·  '.join(bio)}", file=out)
    if c.date_of_birth:
        d = c.date_of_birth
        date_bits = [str(x) for x in (d.year, d.month, d.day) if x is not None]
        if date_bits:
            print(f"  Born:      {'-'.join(date_bits)}", file=out)
    if c.image_url:
        print(f"  Image:     {c.image_url}", file=out)
    if c.description:
        print(f"  About:     {_truncate(c.description, 360)}", file=out)
    return out.getvalue()


def _format_staff_tty(s: Staff) -> str:
    src = f"[src: {s.source.backend}]"
    out = io.StringIO()
    print(f"{s.name}  {src}", file=out)
    if s.name_native:
        print(f"  Native:      {s.name_native}", file=out)
    print(f"  ID:          {s.id}", file=out)
    if s.occupations:
        print(f"  Occupations: {', '.join(s.occupations)}", file=out)
    bio = []
    if s.gender:
        bio.append(f"Gender: {s.gender}")
    if s.age is not None:
        bio.append(f"Age: {s.age}")
    if s.language:
        bio.append(f"Language: {s.language}")
    if s.home_town:
        bio.append(f"Home town: {s.home_town}")
    if s.favourites is not None:
        bio.append(f"Favourites: {s.favourites:,}")
    if bio:
        print(f"  Profile:     {'  ·  '.join(bio)}", file=out)
    if s.years_active:
        print(f"  Years act:   {s.years_active}", file=out)
    if s.date_of_birth:
        d = s.date_of_birth
        date_bits = [str(x) for x in (d.year, d.month, d.day) if x is not None]
        if date_bits:
            print(f"  Born:        {'-'.join(date_bits)}", file=out)
    if s.image_url:
        print(f"  Image:       {s.image_url}", file=out)
    if s.description:
        print(f"  About:       {_truncate(s.description, 360)}", file=out)
    return out.getvalue()


def _format_studio_tty(s: Studio) -> str:
    src = f"[src: {s.source.backend}]"
    out = io.StringIO()
    print(f"{s.name}  {src}", file=out)
    print(f"  ID:               {s.id}", file=out)
    if s.is_animation_studio is not None:
        print(f"  Animation studio: {'yes' if s.is_animation_studio else 'no (licensor / publisher)'}", file=out)
    if s.favourites is not None:
        print(f"  Favourites:       {s.favourites:,}", file=out)
    return out.getvalue()


def _format_trace_hit_tty(h: TraceHit) -> str:
    src = f"[src: {h.source.backend}]"
    title = "(unknown)"
    if h.anilist_title is not None:
        title = h.anilist_title.romaji
        if h.anilist_title.english and h.anilist_title.english != h.anilist_title.romaji:
            title = f"{title} / {h.anilist_title.english}"
    out = io.StringIO()
    print(f"{title}  (anilist:{h.anilist_id})  {src}", file=out)
    if h.anilist_title and h.anilist_title.native:
        print(f"  Native:     {h.anilist_title.native}", file=out)
    if h.episode is not None:
        print(f"  Episode:    {h.episode}", file=out)
    print(
        f"  Frame:      {h.frame_at_seconds:.2f}s  (scene {h.start_at_seconds:.2f}s → {h.end_at_seconds:.2f}s)",
        file=out,
    )
    if h.episode_duration_seconds:
        m, s = divmod(int(h.episode_duration_seconds), 60)
        print(f"  Episode dur: {m}m{s:02d}s", file=out)
    print(f"  Similarity: {h.similarity:.4f}  ({'reliable' if h.similarity >= 0.87 else 'low confidence'})", file=out)
    if h.episode_filename:
        print(f"  Source:     {h.episode_filename}", file=out)
    if h.preview_video_url:
        print(f"  Preview MP4: {h.preview_video_url}", file=out)
    if h.preview_image_url:
        print(f"  Preview JPG: {h.preview_image_url}", file=out)
    return out.getvalue()


def _format_trace_quota_tty(q: TraceQuota) -> str:
    src = f"[src: {q.source.backend}]"
    out = io.StringIO()
    print(f"Trace.moe quota  {src}", file=out)
    print(f"  Tier priority:    {q.priority}  ({'sponsor / patron' if q.priority > 0 else 'anonymous'})", file=out)
    print(f"  Concurrency:      {q.concurrency}", file=out)
    pct = (q.quota_used / q.quota * 100) if q.quota else 0
    print(f"  Used / quota:     {q.quota_used} / {q.quota}  ({pct:.1f}% used)", file=out)
    print(f"  Remaining:        {max(0, q.quota - q.quota_used)}", file=out)
    return out.getvalue()


def _format_airing_schedule_tty(row: AiringScheduleRow) -> str:
    src = f"[src: {row.source.backend}]"
    out = io.StringIO()
    print(f"{row.title}  {src}", file=out)
    if row.airing_at is not None:
        print(f"  Airing:   {row.airing_at.isoformat()}", file=out)
    detail = []
    if row.weekday:
        detail.append(row.weekday)
    if row.local_time:
        detail.append(row.local_time)
    if detail:
        print(f"  Schedule: {'  ·  '.join(detail)}", file=out)
    if row.episode is not None:
        print(f"  Episode:  {row.episode}", file=out)
    return out.getvalue()


def _tzinfo_from_label(label: str):
    if label == "UTC":
        return timezone.utc
    match = _OFFSET_RE.match(label)
    if match is not None:
        sign, hours_text, minutes_text = match.groups()
        delta = timedelta(hours=int(hours_text), minutes=int(minutes_text))
        if sign == "-":
            delta = -delta
        return timezone(delta, name=f"{sign}{int(hours_text):02d}:{int(minutes_text):02d}")
    try:
        return ZoneInfo(label)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _schedule_datetime(row: AiringScheduleRow, *, window_start: date, timezone_label: str) -> Optional[datetime]:
    target_tz = _tzinfo_from_label(timezone_label)
    if row.airing_at is not None:
        return row.airing_at.astimezone(target_tz) if target_tz is not None else row.airing_at
    if row.weekday in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday") and row.local_time:
        try:
            hour, minute = [int(part) for part in row.local_time.split(":", 1)]
        except ValueError:
            return None
        weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        delta = (weekdays.index(row.weekday) - window_start.weekday()) % 7
        tz = target_tz
        return datetime.combine(window_start + timedelta(days=delta), time(hour, minute), tzinfo=tz)
    return None


def _format_schedule_calendar_tty(result: ScheduleCalendarResult) -> str:
    out = io.StringIO()
    print(f"Schedule ({result.timezone})", file=out)
    print(f"Window: {result.window_start.isoformat()} to {result.window_end.isoformat()} (exclusive)", file=out)
    if not result.items:
        return out.getvalue()

    groups = {}
    floating = []
    for item in result.items:
        row = item if isinstance(item, AiringScheduleRow) else None
        if row is None and hasattr(item, "to_common"):
            try:
                common = item.to_common()
            except Exception:
                common = None
            row = common if isinstance(common, AiringScheduleRow) else None
        if row is None:
            floating.append(item)
            continue
        when = _schedule_datetime(row, window_start=result.window_start, timezone_label=result.timezone)
        key = when.date() if when is not None else None
        groups.setdefault(key, []).append((when, row))

    for day in sorted(groups, key=lambda value: value or date.max):
        label = day.strftime("%A, %Y-%m-%d") if day is not None else "Unscheduled"
        print("", file=out)
        print(label, file=out)
        for when, row in sorted(groups[day], key=lambda pair: ((pair[0] or datetime.max).time(), pair[1].title)):
            clock = when.strftime("%H:%M") if when is not None else (row.local_time or "--:--")
            bits = [f"  {clock}", row.title]
            if row.episode is not None:
                bits.append(f"ep {row.episode}")
            bits.append(f"[src: {row.source.backend}]")
            print("  ".join(bits), file=out)

    for item in floating:
        print("", file=out)
        print(render_tty(item) if isinstance(item, AnimedexModel) else str(item), file=out)
    return out.getvalue()


def _format_merged_anime_tty(item: MergedAnime) -> str:
    source_names = "+".join(source.backend for source in item.sources) or "?"
    out = io.StringIO()
    print(f"{item.title.romaji}  [src: {source_names}]", file=out)
    if item.title.english and item.title.english != item.title.romaji:
        print(f"  English: {item.title.english}", file=out)
    if item.ids:
        print(f"  IDs:     {' | '.join(f'{key}:{value}' for key, value in sorted(item.ids.items()))}", file=out)
    for backend, anime in item.records.items():
        bits = []
        if anime.score is not None:
            bits.append(f"score {anime.score.score}/{anime.score.scale}")
        if anime.format:
            bits.append(anime.format)
        if anime.episodes is not None:
            bits.append(f"{anime.episodes} ep")
        if anime.status:
            bits.append(anime.status)
        detail = "  ·  ".join(bits) if bits else anime.id
        title = anime.title.romaji
        print(f"  {backend}: {title}  ({detail})", file=out)
    return out.getvalue()


def render_tty(model: AnimedexModel) -> str:
    """Render a model into the human-friendly TTY form.

    Dispatches on type: :class:`Anime`, :class:`Character`,
    :class:`Staff`, :class:`Studio`, :class:`TraceHit`, and
    :class:`TraceQuota` each get a multi-line block. Other models
    fall back to a default representation that still carries the
    source marker.

    :param model: The :class:`AnimedexModel` instance to render.
    :type model: AnimedexModel
    :return: The TTY-friendly string.
    :rtype: str
    """
    if isinstance(model, ScheduleCalendarResult):
        return _format_schedule_calendar_tty(model)
    if isinstance(model, AggregateResult):
        if not model.items:
            return ""
        return "\n\n".join(render_tty(item) if isinstance(item, AnimedexModel) else str(item) for item in model.items)
    if isinstance(model, MergedAnime):
        return _format_merged_anime_tty(model)
    if isinstance(model, AiringScheduleRow):
        return _format_airing_schedule_tty(model)
    if isinstance(model, Anime):
        return _format_anime_tty(model)
    if isinstance(model, Character):
        return _format_character_tty(model)
    if isinstance(model, Staff):
        return _format_staff_tty(model)
    if isinstance(model, Studio):
        return _format_studio_tty(model)
    if isinstance(model, TraceHit):
        return _format_trace_hit_tty(model)
    if isinstance(model, TraceQuota):
        return _format_trace_quota_tty(model)
    # Rich per-backend dataclass (AnilistAnime / AnilistCharacter /
    # AnilistStaff / AnilistStudio / JikanAnime / JikanCharacter /
    # ...) — project to the common type and re-render. The common
    # types have human-friendly formatters above; rich types either
    # implement ``to_common()`` (which projects onto a common type
    # and recurses here) or fall through to the JSON-dump fallback
    # below. ``JikanGenericResponse`` is an example of the latter:
    # its row shape is too varied for a single TTY formatter.
    if hasattr(model, "to_common"):
        try:
            common = model.to_common()
        except Exception:
            common = None
        if isinstance(common, (Anime, AiringScheduleRow, Character, Staff, Studio)):
            return render_tty(common)
    # Generic fallback: dump JSON with whichever SourceTag we can find.
    # Rich dataclasses store the SourceTag on ``source_tag`` because
    # their ``source`` field is already taken by upstream metadata
    # (Jikan ``source: "Manga"``, AniList ``source: "MANGA"``). Look
    # at ``source_tag`` first, fall back to ``source`` only when it
    # really is a :class:`SourceTag` instance.
    from animedex.models.common import SourceTag

    src = getattr(model, "source_tag", None)
    if not isinstance(src, SourceTag):
        candidate = getattr(model, "source", None)
        src = candidate if isinstance(candidate, SourceTag) else None
    src_marker = f"[src: {src.backend}]" if src is not None else "[src: ?]"
    # ``by_alias=True`` so backend rich models with aliased fields
    # (e.g. ``RawTraceHit.from_`` aliased to ``from``) preserve the
    # upstream key names in this fallback path too — matching what
    # the JSON renderer emits.
    return f"{type(model).__name__} {src_marker}\n{model.model_dump_json(by_alias=True)}\n"


def render_for_stream(model: AnimedexModel, stream: Any) -> str:
    """Render the way the CLI does for a given stream.

    When ``stream`` is a TTY, returns the TTY-friendly output;
    otherwise returns source-attributed JSON. This is the single
    entry point CLI commands call so the "TTY vs pipe" decision
    lives in one place.

    :param model: The :class:`AnimedexModel` instance to render.
    :type model: AnimedexModel
    :param stream: Destination stream (typically ``sys.stdout``).
    :type stream: Any
    :return: Rendered payload.
    :rtype: str
    """
    if is_terminal(stream):
        return render_tty(model)
    return render_json(model, include_source=True)


def selftest() -> bool:
    """Smoke-test the TTY renderer and the auto-switch.

    :return: ``True`` on success.
    :rtype: bool
    """
    from datetime import datetime, timezone

    from animedex.models.anime import Anime, AnimeTitle
    from animedex.models.common import SourceTag

    a = Anime(
        id="_st:1",
        title=AnimeTitle(romaji="x"),
        ids={},
        source=SourceTag(backend="_st", fetched_at=datetime.now(timezone.utc)),
    )
    out_tty = render_tty(a)
    assert "[src: _st]" in out_tty

    class FakeTty:
        def isatty(self):
            return True

    class FakePipe:
        def isatty(self):
            return False

    assert "[src: _st]" in render_for_stream(a, FakeTty())
    assert render_for_stream(a, FakePipe()).startswith("{")
    return True
