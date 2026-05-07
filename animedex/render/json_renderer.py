"""
JSON renderer with optional source attribution.

When :func:`render_json` is called with ``include_source=True`` (the
default), the resulting JSON carries a top-level ``_meta`` block and
preserves the ``source`` field from the model. Setting
``include_source=False`` strips the meta block (per ``plans/03 §9``
``--source-attribution=off``); the per-field ``source`` keys remain
in place because they are part of the model schema and removing them
selectively is the renderer's job, not pydantic's.
"""

from __future__ import annotations

import json
from typing import Any

from animedex.models.common import AnimedexModel


def _drop_meta(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned = {key: _drop_meta(value) for key, value in payload.items() if key != "_meta"}
        return cleaned
    if isinstance(payload, list):
        return [_drop_meta(item) for item in payload]
    return payload


def render_json(model: AnimedexModel, *, include_source: bool = True) -> str:
    """Render a model to a JSON string.

    The function emits the same field-level shape pydantic would
    produce via :meth:`AnimedexModel.model_dump_json`; when
    ``include_source`` is true it additionally injects a top-level
    ``_meta`` block that names the upstream(s) consulted, derived
    from the ``source`` field on the model. The block lets a CLI
    consumer answer "where did this row come from" without inspecting
    every field.

    :param model: The :class:`AnimedexModel` instance to render.
    :type model: AnimedexModel
    :param include_source: When ``True`` (default), include the
                            ``_meta.sources_consulted`` block. When
                            ``False``, omit it (this matches the
                            ``--source-attribution=off`` flag).
    :type include_source: bool
    :return: A JSON-encoded string.
    :rtype: str
    """
    payload = model.model_dump(mode="json")
    if include_source:
        sources = []
        # Single-source records keep the source on `.source`; merged
        # records (Phase 5 aggregate path) populate `.sources` as a
        # list. Either way we emit one canonical list.
        src = payload.get("source")
        if isinstance(src, dict) and "backend" in src:
            sources.append(src["backend"])
        srcs = payload.get("sources")
        if isinstance(srcs, list):
            for entry in srcs:
                if isinstance(entry, dict) and entry.get("backend"):
                    sources.append(entry["backend"])
        payload["_meta"] = {"sources_consulted": sources}
    else:
        payload = _drop_meta(payload)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def selftest() -> bool:
    """Smoke-test the JSON renderer.

    Round-trips a representative anime model through both
    ``include_source`` flavours and verifies the resulting payload
    decodes and carries the expected keys.

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
    decoded_with = json.loads(render_json(a, include_source=True))
    assert decoded_with["_meta"]["sources_consulted"] == ["_st"]
    decoded_without = json.loads(render_json(a, include_source=False))
    assert "_meta" not in decoded_without
    return True
