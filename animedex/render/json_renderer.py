"""
JSON renderer with optional source attribution.

When :func:`render_json` is called with ``include_source=True`` (the
default), the resulting JSON carries a top-level ``_meta`` block and
preserves the ``source`` field from the model. Setting
``include_source=False`` returns the model's clean
:meth:`pydantic.BaseModel.model_dump` form: per-field ``source`` keys
remain (they are part of the schema), but no ``_meta`` is injected.
"""

from __future__ import annotations

import json

from animedex.models.common import AnimedexModel


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
    # ``by_alias=True`` so backend rich models with aliased fields
    # (``RawTraceHit.from_`` aliased to ``from``, ``JikanAired.from_``)
    # round-trip through the renderer with their upstream key names
    # rather than Python field names. Common projection types don't
    # use aliases, so the flag is a no-op for them.
    payload = model.model_dump(mode="json", by_alias=True)
    if include_source:
        sources = []
        # Single-source records keep the source on either ``.source``
        # (common projection types like :class:`Anime`,
        # :class:`Character`) or ``.source_tag`` (backend-rich types
        # like :class:`AnilistAnime`, :class:`JikanAnime`,
        # :class:`RawTraceHit`, whose ``source`` field is taken by
        # the upstream's own value — Jikan's ``"Manga"`` / AniList's
        # ``"MANGA"``). Inspect both, take whichever is a
        # SourceTag-shaped dict.
        #
        # Merged-source records populate ``.sources`` as a list of
        # SourceTag-shaped dicts; we then emit one canonical list of
        # backend names.
        for key in ("source", "source_tag"):
            candidate = payload.get(key)
            if isinstance(candidate, dict) and "backend" in candidate and "fetched_at" in candidate:
                sources.append(candidate["backend"])
                break  # first SourceTag-shaped wins; don't double-count
        srcs = payload.get("sources")
        if isinstance(srcs, list):
            for entry in srcs:
                if isinstance(entry, dict) and entry.get("backend"):
                    sources.append(entry["backend"])
        payload["_meta"] = {"sources_consulted": sources}
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
