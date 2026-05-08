"""
Ground-floor types every animedex backend, model, and renderer depends on.

This module owns the types that participate in the source-attribution
contract from ``plans/03-cli-architecture-gh-flavored.md`` (the
:class:`SourceTag` carrier; :class:`AnimedexModel` base) and the
small typed surface the library uses to talk about HTTP-shaped facts
(:class:`Pagination`, :class:`RateLimit`, :class:`ApiError`).

The pydantic v2 base class :class:`AnimedexModel` fixes a single,
project-wide configuration: models are immutable (``frozen=True``),
silently ignore unknown upstream fields (``extra='ignore'``), and
accept both alias and field name on input (``populate_by_name=True``).
This is enforced once here so individual backend modules do not drift.

The module also exposes a :func:`selftest` callable the diagnostic
runner picks up; it instantiates representative samples of every type
to confirm the schema parses end-to-end.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AnimedexModel(BaseModel):
    """Project-wide pydantic v2 base for **common projection** types.

    Common types (e.g. :class:`~animedex.models.anime.Anime`,
    :class:`~animedex.models.character.Character`,
    :class:`~animedex.models.character.Staff`,
    :class:`~animedex.models.character.Studio`) are deliberately the
    "lowest common denominator" the project surfaces across multiple
    upstreams. They drop backend-specific fields by design — that is
    the whole point of a projection. ``extra='ignore'`` enforces this
    policy: any field a backend gives us that the projection didn't
    declare is dropped silently.

    Backend-specific **rich** types (``AnilistAnime``, ``JikanAnime``,
    etc.) are NOT this. See :class:`BackendRichModel` below — they
    must be lossless.

    :ivar model_config: pydantic configuration; do not override per
                         subclass without a documented reason.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )


class BackendRichModel(AnimedexModel):
    """Project-wide pydantic v2 base for **backend rich** dataclasses.

    Every per-backend rich type — ``AnilistAnime``, ``AnilistCharacter``,
    ``AnilistStaff``, ``AnilistStudio``, the long-tail Anilist*
    types, ``JikanAnime``, ``JikanCharacter``, ``JikanPerson``,
    ``JikanProducer``, ``JikanClub``, ``JikanUser``, ``JikanGenericRow``,
    ``RawTraceHit``, ``RawTraceQuota``, plus their nested helper types
    (e.g. ``_AnilistTitle``, ``JikanEntity``, ``JikanAired``) —
    inherits from this class.

    The contract: a rich model is **information-lossless**. When fed
    the raw upstream payload via ``model_validate``, it must retain
    every key the upstream returned, so ``model_dump(by_alias=True,
    mode='json')`` reconstructs the original payload field-for-field.

    Achieved by:

    * ``extra='allow'`` — fields the model didn't declare are kept on
      the instance and re-emitted on dump (instead of silently
      dropped, which is what :class:`AnimedexModel` does for common
      projections).
    * ``populate_by_name=True`` — alias-renamed fields (e.g.
      ``from_: float = Field(alias='from')`` for the Python keyword
      conflict) accept either form on input.

    The class **inherits from** :class:`AnimedexModel` rather than
    sitting beside it. Pydantic v2 merges ``model_config`` across
    inheritance, so the ``extra='allow'`` here overrides the parent's
    ``extra='ignore'``. The inheritance matters: every ``isinstance(x,
    AnimedexModel)`` check downstream (the TTY dispatcher in
    :mod:`animedex.render.tty`, the JSON renderer, the CLI's
    ``_to_tty_text`` helper) must continue to recognise rich
    instances. Splitting the two roots was a bug that made rich models
    fall through to ``str(x)`` and dump pydantic ``__repr__`` instead
    of human-friendly TTY text.

    Backend-rich → common projection happens via the rich type's
    ``to_common()`` method. Loss of fields is permitted at and only
    at that boundary.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        populate_by_name=True,
    )


class SourceTag(AnimedexModel):
    """Provenance carrier attached to every backend-returned record.

    Per ``plans/03-cli-architecture-gh-flavored.md`` §5, every datum
    surfaced by animedex must carry the upstream that produced it.
    :class:`SourceTag` is the typed form of that contract: the TTY
    renderer prints ``[src: <backend>]`` from it, the JSON renderer
    emits ``_source`` from it, and the cache layer records it.

    :ivar backend: Short upstream identifier
                    (e.g. ``"anilist"``, ``"jikan"``, ``"kitsu"``).
    :vartype backend: str
    :ivar fetched_at: When this datum was retrieved (or, for a cache
                       hit, when it was originally retrieved).
    :vartype fetched_at: datetime.datetime
    :ivar cached: ``True`` when the value was served from local cache
                   rather than a fresh upstream call.
    :vartype cached: bool
    :ivar rate_limited: ``True`` when fetching this datum required
                         waiting for a rate-limit window.
    :vartype rate_limited: bool
    """

    backend: str
    fetched_at: datetime
    cached: bool = False
    rate_limited: bool = False


class PartialDate(AnimedexModel):
    """A date where any of year/month/day may be unknown.

    AniList's ``dateOfBirth`` / ``startDate`` / ``endDate`` shapes
    return ``{ year, month, day }`` with each component independently
    nullable. A character may have a known birth-month but no day; a
    series may be year-only when the exact air date isn't recorded.
    :class:`datetime.date` cannot represent that, so this lighter-
    weight type stands in.

    :ivar year: Calendar year when known.
    :vartype year: int or None
    :ivar month: Calendar month (1-12) when known.
    :vartype month: int or None
    :ivar day: Day of month (1-31) when known.
    :vartype day: int or None
    """

    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None


class Pagination(AnimedexModel):
    """Page cursor accompanying list responses.

    :ivar page: Current page index, 1-based.
    :vartype page: int
    :ivar per_page: Items returned per page.
    :vartype per_page: int
    :ivar total: Total item count when the upstream exposes it.
    :vartype total: int or None
    :ivar has_next: Whether another page is available.
    :vartype has_next: bool
    """

    page: int
    per_page: int
    total: Optional[int] = None
    has_next: bool = False


class RateLimit(AnimedexModel):
    """Snapshot of an upstream's rate-limit posture for a single call.

    :ivar remaining: Calls remaining in the current window when
                      reported.
    :vartype remaining: int or None
    :ivar reset_at: When the current window resets.
    :vartype reset_at: datetime.datetime
    """

    remaining: Optional[int] = None
    reset_at: datetime


class ApiError(Exception):
    """Typed error raised by the transport, cache, and policy layers.

    Carries a structured ``backend`` and ``reason`` so the CLI can
    render a stable, machine-grepable message without parsing free
    text. The string form of the exception always includes both
    fields when set.

    :param message: Human-readable description of the failure.
    :type message: str
    :param backend: Backend identifier when the failure is
                     backend-specific.
    :type backend: str or None
    :param reason: Short slug categorising the failure (e.g.
                    ``"rate-limited"``, ``"read-only"``,
                    ``"upstream-5xx"``).
    :type reason: str or None
    """

    def __init__(
        self,
        message: str,
        *,
        backend: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.backend = backend
        self.reason = reason

    def __str__(self) -> str:
        prefix_bits = []
        if self.backend is not None:
            prefix_bits.append(f"backend={self.backend}")
        if self.reason is not None:
            prefix_bits.append(f"reason={self.reason}")
        if prefix_bits:
            return f"[{' '.join(prefix_bits)}] {self.message}"
        return self.message


def selftest() -> bool:
    """Smoke-test the types end-to-end.

    The diagnostic runner (:func:`animedex.diag.run_selftest`)
    invokes this; the function instantiates each public type so that
    pydantic schema construction is exercised. Anything that would
    fail at first use - missing field, wrong default, broken alias -
    surfaces here in milliseconds, before the CLI tries to render a
    real backend response.

    :return: ``True`` when the model graph parses. Raises on schema
             errors so the runner reports them with a traceback.
    :rtype: bool
    """
    now = datetime.now(timezone.utc)
    SourceTag(backend="_selftest", fetched_at=now)
    SourceTag.model_validate({"backend": "_selftest", "fetched_at": now.isoformat()})
    PartialDate(year=2026, month=5, day=7)
    PartialDate(year=2026)
    PartialDate()
    Pagination(page=1, per_page=20, has_next=False)
    RateLimit(reset_at=now)
    err = ApiError("smoke", backend="_selftest", reason="selftest")
    str(err)
    # AnimedexModel and Any are re-exports; importing them at the
    # top of the module is sufficient confirmation that the public
    # surface loads.
    return True
