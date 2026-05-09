"""Rich AnimeChan dataclasses.

AnimeChan wraps quote reads as ``{"status": "success", "data": ...}``
and each quote carries the text plus nested anime and character
objects. The high-level helpers validate the inner quote records
through :class:`AnimeChanQuote`; the enclosing response model is kept
for lossless fixture verification.
"""

from __future__ import annotations

from typing import List, Optional, Union

from animedex.models.common import BackendRichModel, SourceTag
from animedex.models.quote import Quote


class AnimeChanAnime(BackendRichModel):
    """Nested anime object on an AnimeChan quote."""

    id: Optional[int] = None
    name: Optional[str] = None
    altName: Optional[str] = None


class AnimeChanCharacter(BackendRichModel):
    """Nested character object on an AnimeChan quote."""

    id: Optional[int] = None
    name: Optional[str] = None


class AnimeChanQuote(BackendRichModel):
    """One quote record from AnimeChan."""

    content: str
    anime: Optional[AnimeChanAnime] = None
    character: Optional[AnimeChanCharacter] = None
    source_tag: Optional[SourceTag] = None

    def to_common(self) -> Quote:
        """Project this quote onto the cross-source quote shape.

        :return: Cross-source projection.
        :rtype: animedex.models.quote.Quote
        """
        return Quote(
            text=self.content,
            anime=self.anime.name if self.anime else None,
            character=self.character.name if self.character else None,
            source=self.source_tag or _default_src(),
        )


class AnimeChanEnvelope(BackendRichModel):
    """AnimeChan response envelope for a single quote or quote list."""

    status: Optional[str] = None
    data: Optional[Union[AnimeChanQuote, List[AnimeChanQuote]]] = None
    message: Optional[str] = None
    source_tag: Optional[SourceTag] = None


def _default_src() -> SourceTag:
    """Construct a fallback source tag for direct model usage."""
    from datetime import datetime, timezone

    return SourceTag(backend="quote", fetched_at=datetime.now(timezone.utc))


def selftest() -> bool:
    """Smoke-test the AnimeChan rich models.

    Validates a representative quote envelope, confirms nested anime
    and character models round-trip, and checks ``to_common()`` maps
    text, anime name, character name, and source attribution.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="quote", fetched_at=datetime.now(timezone.utc))
    row = {
        "content": "Sample quote.",
        "anime": {"id": 1, "name": "Sample Anime", "altName": "Sample Alt"},
        "character": {"id": 2, "name": "Sample Character"},
        "source_tag": src.model_dump(),
    }
    quote = AnimeChanQuote.model_validate(row)
    AnimeChanQuote.model_validate_json(quote.model_dump_json())
    common = quote.to_common()
    assert common.text == "Sample quote."
    assert common.anime == "Sample Anime"
    assert common.character == "Sample Character"
    assert common.source.backend == "quote"
    env = AnimeChanEnvelope.model_validate({"status": "success", "data": row, "source_tag": src.model_dump()})
    assert env.status == "success"
    return True
