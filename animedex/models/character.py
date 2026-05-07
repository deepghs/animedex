"""
Character / staff / studio domain models.

These records come from AniList's character / staff / studio
endpoints and surface as their own subcommands in the Phase 2 CLI.
The trio shares a structural pattern - id, name, source - and adds a
small number of role-specific optional fields.
"""

from __future__ import annotations

from typing import Optional

from animedex.models.common import AnimedexModel, SourceTag


class Character(AnimedexModel):
    """A fictional character.

    :ivar id: Canonical ``"<source>:char:<id>"`` identifier.
    :vartype id: str
    :ivar name: Display name (typically romaji).
    :vartype name: str
    :ivar role: Casting role when reported (e.g. ``"MAIN"``,
                 ``"SUPPORTING"``).
    :vartype role: str or None
    :ivar image_url: Portrait URL when one is available.
    :vartype image_url: str or None
    :ivar description: Free-text description from upstream.
    :vartype description: str or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    role: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    source: SourceTag


class Staff(AnimedexModel):
    """A production staff member.

    :ivar id: Canonical ``"<source>:staff:<id>"`` identifier.
    :vartype id: str
    :ivar name: Display name.
    :vartype name: str
    :ivar primary_role: Most-credited role (e.g. ``"Director"``,
                         ``"Composer"``).
    :vartype primary_role: str or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    primary_role: Optional[str] = None
    source: SourceTag


class Studio(AnimedexModel):
    """A production studio.

    :ivar id: Canonical ``"<source>:studio:<id>"`` identifier.
    :vartype id: str
    :ivar name: Studio name.
    :vartype name: str
    :ivar is_animation_studio: ``True`` for animation studios,
                                ``False`` for licensors etc., ``None``
                                when the upstream does not report.
    :vartype is_animation_studio: bool or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    is_animation_studio: Optional[bool] = None
    source: SourceTag


def selftest() -> bool:
    """Smoke-test the character / staff / studio model graph.

    :return: ``True`` on success; raises on schema errors.
    :rtype: bool
    """
    from datetime import datetime, timezone

    src = SourceTag(backend="_selftest", fetched_at=datetime.now(timezone.utc))
    Character.model_validate_json(
        Character(
            id="_c", name="x", role="MAIN", image_url="https://x.invalid/c.jpg", description="d", source=src
        ).model_dump_json()
    )
    Staff.model_validate_json(Staff(id="_s", name="x", primary_role="Director", source=src).model_dump_json())
    Studio.model_validate_json(Studio(id="_st", name="x", is_animation_studio=True, source=src).model_dump_json())
    return True
