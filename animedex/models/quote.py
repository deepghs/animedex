"""
Anime-quote model.

:class:`Quote` is the shape AnimeChan returns. The free-tier API
exposes only the random-quote endpoint, so the typed surface is
small; ``character`` and ``anime`` are optional because some quotes
omit one or the other.
"""

from __future__ import annotations

from typing import Optional

from animedex.models.common import AnimedexModel, SourceTag


class Quote(AnimedexModel):
    """A single anime quote.

    :ivar text: The quote text.
    :vartype text: str
    :ivar character: Speaker name when reported.
    :vartype character: str or None
    :ivar anime: Source anime title when reported.
    :vartype anime: str or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    text: str
    character: Optional[str] = None
    anime: Optional[str] = None
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the quote model.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    q = Quote(text="x", character="y", anime="z", source=src)
    Quote.model_validate_json(q.model_dump_json())
    return True
