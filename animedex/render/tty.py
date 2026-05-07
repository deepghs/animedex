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
from typing import Any

from animedex.models.anime import Anime
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import AnimedexModel
from animedex.models.trace import TraceHit, TraceQuota
from animedex.render.json_renderer import render_json


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


def _format_anime_tty(anime: Anime) -> str:
    src_marker = f"[src: {anime.source.backend}]"
    out = io.StringIO()
    print(f"{anime.title.romaji}", file=out)
    if anime.title.english:
        print(f"  English: {anime.title.english}", file=out)
    print(f"  ID: {anime.id} {src_marker}", file=out)
    if anime.episodes is not None:
        print(f"  Episodes: {anime.episodes} {src_marker}", file=out)
    if anime.studios:
        print(f"  Studios: {', '.join(anime.studios)} {src_marker}", file=out)
    if anime.score is not None:
        print(f"  Score: {anime.score.score} / {anime.score.scale} {src_marker}", file=out)
    if anime.streaming:
        for link in anime.streaming:
            print(f"  Streaming: {link.provider} -> {link.url} {src_marker}", file=out)
    return out.getvalue()


def _format_character_tty(c: Character) -> str:
    src = f"[src: {c.source.backend}]"
    out = io.StringIO()
    print(f"{c.name} {src}", file=out)
    if c.name_native:
        print(f"  Native: {c.name_native}", file=out)
    if c.name_alternatives:
        print(f"  Alt names: {', '.join(c.name_alternatives)}", file=out)
    print(f"  ID: {c.id}", file=out)
    if c.role:
        print(f"  Role: {c.role}", file=out)
    if c.gender:
        print(f"  Gender: {c.gender}", file=out)
    if c.age:
        print(f"  Age: {c.age}", file=out)
    if c.favourites is not None:
        print(f"  Favourites: {c.favourites}", file=out)
    return out.getvalue()


def _format_staff_tty(s: Staff) -> str:
    src = f"[src: {s.source.backend}]"
    out = io.StringIO()
    print(f"{s.name} {src}", file=out)
    if s.name_native:
        print(f"  Native: {s.name_native}", file=out)
    print(f"  ID: {s.id}", file=out)
    if s.occupations:
        print(f"  Occupations: {', '.join(s.occupations)}", file=out)
    if s.language:
        print(f"  Language: {s.language}", file=out)
    if s.home_town:
        print(f"  Home town: {s.home_town}", file=out)
    if s.years_active:
        print(f"  Years active: {s.years_active}", file=out)
    if s.favourites is not None:
        print(f"  Favourites: {s.favourites}", file=out)
    return out.getvalue()


def _format_studio_tty(s: Studio) -> str:
    src = f"[src: {s.source.backend}]"
    out = io.StringIO()
    print(f"{s.name} {src}", file=out)
    print(f"  ID: {s.id}", file=out)
    if s.is_animation_studio is not None:
        print(f"  Animation studio: {s.is_animation_studio}", file=out)
    if s.favourites is not None:
        print(f"  Favourites: {s.favourites}", file=out)
    return out.getvalue()


def _format_trace_hit_tty(h: TraceHit) -> str:
    src = f"[src: {h.source.backend}]"
    title = "(unknown)"
    if h.anilist_title is not None:
        title = h.anilist_title.romaji
    out = io.StringIO()
    print(f"{title} (anilist:{h.anilist_id}) {src}", file=out)
    if h.episode is not None:
        print(f"  Episode: {h.episode}", file=out)
    print(f"  Frame: {h.frame_at_seconds:.2f}s (scene {h.start_at_seconds:.2f}–{h.end_at_seconds:.2f}s)", file=out)
    print(f"  Similarity: {h.similarity:.4f}", file=out)
    if h.episode_filename:
        print(f"  Source: {h.episode_filename}", file=out)
    if h.preview_video_url:
        print(f"  Preview: {h.preview_video_url}", file=out)
    return out.getvalue()


def _format_trace_quota_tty(q: TraceQuota) -> str:
    src = f"[src: {q.source.backend}]"
    out = io.StringIO()
    print(f"Trace.moe quota {src}", file=out)
    print(f"  Tier priority: {q.priority}", file=out)
    print(f"  Concurrency:   {q.concurrency}", file=out)
    print(f"  Used / quota:  {q.quota_used} / {q.quota}", file=out)
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
    src = getattr(model, "source", None)
    src_marker = f"[src: {src.backend}]" if src is not None else "[src: ?]"
    return f"{type(model).__name__} {src_marker}\n{model.model_dump_json()}\n"


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
