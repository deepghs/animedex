"""Rich nekos.best dataclasses (one per response shape).

nekos.best v2 has a tiny surface — three JSON-emitting endpoints —
but each carries enough metadata to make the SFW image collection
useful both as a CLI grab-bag and as a Python library lookup.

The two rich shapes pinned here are deliberately per-record, not
per-endpoint:

* :class:`NekosImage` — one image / GIF record. Comes back from
  ``/<category>?amount=N`` (each row in ``results``) and from
  ``/search`` (each row in ``results``).
* :class:`NekosCategoryFormat` — one ``{format, min, max}`` entry
  from ``/endpoints``. The upstream emits a flat
  ``{<category>: {format, min, max}, ...}`` map, so the per-record
  type is what makes the lossless round-trip contract well-defined.

The :class:`NekosImage` ``to_common()`` projects an upstream record
onto the cross-source :class:`~animedex.models.art.ArtPost`. The
projection is deterministic:

* ``rating`` is always ``"g"`` (nekos.best v2 has no NSFW tier).
* ``id`` is composed as ``"nekos:" + filename`` — nekos.best has no
  numeric ID column, but every URL ends in a stable filename, so the
  filename is the canonical identifier.
* ``tags`` carries the upstream's ``anime_name`` (when present) so a
  cross-source pipeline can match against
  :class:`~animedex.models.anime.Anime` by show.
"""

from __future__ import annotations

from typing import List, Optional

from animedex.models.art import ArtPost
from animedex.models.common import BackendRichModel, SourceTag


class NekosImage(BackendRichModel):
    """A single image / GIF record from nekos.best v2.

    Every record exposes ``url``; the rest of the fields are
    best-effort attribution. ``anime_name`` and ``artist_name`` are
    the typical attribution columns; ``source_url`` points at the
    artist's gallery or the anime's page when available.

    :ivar url: Direct asset URL.
    :vartype url: str
    :ivar anime_name: Show name when the asset is anime-derived.
    :vartype anime_name: str or None
    :ivar artist_name: Artist attribution when the asset is fan art.
    :vartype artist_name: str or None
    :ivar artist_href: Artist's profile / portfolio URL.
    :vartype artist_href: str or None
    :ivar source_url: Original source URL (pixiv / twitter / official
                       site / etc.).
    :vartype source_url: str or None
    :ivar source_tag: Provenance tag stamped by the high-level
                       fetch helper.
    :vartype source_tag: SourceTag or None
    """

    url: str
    anime_name: Optional[str] = None
    artist_name: Optional[str] = None
    artist_href: Optional[str] = None
    source_url: Optional[str] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> ArtPost:
        """Project this image record onto the cross-source
        :class:`~animedex.models.art.ArtPost` shape.

        ``rating`` is always ``"g"`` (nekos.best v2 is SFW-only).
        ``id`` derives from the URL's filename, the only stable
        per-asset identifier nekos.best exposes. The upstream's
        ``anime_name`` is propagated into ``tags`` so cross-source
        consumers can match on show without an extra round-trip.

        :return: Cross-source projection.
        :rtype: animedex.models.art.ArtPost
        """
        filename = self.url.rsplit("/", 1)[-1] if self.url else "unknown"
        tags: List[str] = []
        if self.anime_name:
            tags.append(self.anime_name)
        return ArtPost(
            id=f"nekos:{filename}",
            url=self.url,
            rating="g",
            tags=tags,
            artist=self.artist_name,
            source_url=self.source_url,
            source=self.source_tag or _default_src(),
        )


class NekosCategoryFormat(BackendRichModel):
    """Per-category format entry exposed by ``/endpoints``.

    Each category advertises a single asset format (``"png"`` or
    ``"gif"``) plus the ``min`` / ``max`` filename suffix range used
    by the ``/<category>/<filename>.<format>`` direct-asset
    retrieval. The flat ``/endpoints`` payload is a map from category
    name to one of these entries.

    :ivar format: Asset format (``"png"`` or ``"gif"``).
    :vartype format: str or None
    :ivar min: Smallest filename suffix in the category.
    :vartype min: str or None
    :ivar max: Largest filename suffix in the category.
    :vartype max: str or None
    """

    format: Optional[str] = None
    min: Optional[str] = None
    max: Optional[str] = None


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` when one isn't already
    attached. Used by :meth:`NekosImage.to_common` for direct-from-
    JSON construction paths that bypass the high-level fetch helper.
    """
    from datetime import datetime, timezone

    return SourceTag(backend="nekos", fetched_at=datetime.now(timezone.utc))


def selftest() -> bool:
    """Smoke-test the nekos models.

    Validates a synthetic :class:`NekosImage` round-trips through
    ``model_dump_json`` / ``model_validate_json`` and projects to a
    well-formed :class:`~animedex.models.art.ArtPost` — pinning the
    SFW-only ``rating='g'`` invariant. Also validates a synthetic
    :class:`NekosCategoryFormat`.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    img = NekosImage(
        url="https://nekos.best/api/v2/husbando/0001.png",
        anime_name="Sample",
        artist_name="An Artist",
        source_url="https://x.invalid/gallery",
        source_tag=src,
    )
    NekosImage.model_validate_json(img.model_dump_json())
    common = img.to_common()
    assert common.rating == "g"
    assert common.id == "nekos:0001.png"
    assert common.tags == ["Sample"]
    fmt = NekosCategoryFormat.model_validate({"format": "png", "min": "0001", "max": "9999"})
    assert fmt.format == "png"
    return True
