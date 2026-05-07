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
from animedex.models.common import AnimedexModel
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


def render_tty(model: AnimedexModel) -> str:
    """Render a model into the human-friendly TTY form.

    Currently dispatches on type: :class:`Anime` gets a
    multi-line block; other models fall back to a default
    representation that still carries the source marker.

    :param model: The :class:`AnimedexModel` instance to render.
    :type model: AnimedexModel
    :return: The TTY-friendly string.
    :rtype: str
    """
    if isinstance(model, Anime):
        return _format_anime_tty(model)
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
