"""
Character / staff / studio domain models.

These records come from AniList's character / staff / studio
endpoints and surface as their own subcommands in the Phase 2 CLI.
The trio shares a structural pattern - id, name, source - and adds a
small number of role-specific optional fields.

Phase 2 expanded each model based on real-data reconnaissance against
AniList (see issue #5 §2). The added fields (gender / age / dates /
favourites / native names) are populated by AniList; backends that
don't expose them leave them ``None``.
"""

from __future__ import annotations

from typing import List, Optional

from animedex.models.common import AnimedexModel, PartialDate, SourceTag


class Character(AnimedexModel):
    """A fictional character.

    :ivar id: Canonical ``"<source>:char:<id>"`` identifier.
    :vartype id: str
    :ivar name: Display name (typically romaji / English).
    :vartype name: str
    :ivar name_native: Native-script name (typically Japanese).
    :vartype name_native: str or None
    :ivar name_alternatives: Alternative names / nicknames.
    :vartype name_alternatives: list of str
    :ivar role: Casting role when reported (e.g. ``"MAIN"``,
                 ``"SUPPORTING"``).
    :vartype role: str or None
    :ivar image_url: Portrait URL when one is available.
    :vartype image_url: str or None
    :ivar description: Free-text description from upstream.
    :vartype description: str or None
    :ivar gender: Free-form gender string ("Male", "Female",
                   "Non-binary", ...). Upstream vocabularies vary.
    :vartype gender: str or None
    :ivar age: Free-form age string. AniList sometimes returns a
                composite (e.g. ``"55 | 13 (after 5-year gap)"``) so
                the field is left as a string rather than coerced.
    :vartype age: str or None
    :ivar date_of_birth: Birthday with any of year/month/day potentially
                          unknown.
    :vartype date_of_birth: PartialDate or None
    :ivar favourites: Number of users that marked this character as a
                       favourite (AniList-specific signal).
    :vartype favourites: int or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    name_native: Optional[str] = None
    name_alternatives: List[str] = []
    role: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    date_of_birth: Optional[PartialDate] = None
    favourites: Optional[int] = None
    source: SourceTag


class Staff(AnimedexModel):
    """A production staff member.

    :ivar id: Canonical ``"<source>:staff:<id>"`` identifier.
    :vartype id: str
    :ivar name: Display name.
    :vartype name: str
    :ivar name_native: Native-script name.
    :vartype name_native: str or None
    :ivar occupations: Production roles, in upstream order.
                        Empty list when the upstream does not report.
    :vartype occupations: list of str
    :ivar gender: Free-form gender string.
    :vartype gender: str or None
    :ivar age: Numeric age when reported. Upstream returns this as int.
    :vartype age: int or None
    :ivar date_of_birth: Birthday with partial precision.
    :vartype date_of_birth: PartialDate or None
    :ivar years_active: Years (or year ranges) the staff was professionally
                         active. Upstream returns 0-2 ints (start / end).
    :vartype years_active: list of int
    :ivar home_town: Birthplace city / region.
    :vartype home_town: str or None
    :ivar language: Primary working language (e.g. ``"Japanese"``,
                     ``"English"``).
    :vartype language: str or None
    :ivar image_url: Portrait URL.
    :vartype image_url: str or None
    :ivar description: Free-text bio.
    :vartype description: str or None
    :ivar favourites: Count of users marking the staff as favourite.
    :vartype favourites: int or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    name_native: Optional[str] = None
    occupations: List[str] = []
    gender: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[PartialDate] = None
    years_active: List[int] = []
    home_town: Optional[str] = None
    language: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    favourites: Optional[int] = None
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
    :ivar favourites: User-favourite count.
    :vartype favourites: int or None
    :ivar source: Provenance tag.
    :vartype source: SourceTag
    """

    id: str
    name: str
    is_animation_studio: Optional[bool] = None
    favourites: Optional[int] = None
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
            id="_c",
            name="x",
            name_native="ネイティブ",
            name_alternatives=["nick"],
            role="MAIN",
            image_url="https://x.invalid/c.jpg",
            description="d",
            gender="Female",
            age="62",
            date_of_birth=PartialDate(year=1962, month=4, day=15),
            favourites=42,
            source=src,
        ).model_dump_json()
    )
    Staff.model_validate_json(
        Staff(
            id="_s",
            name="x",
            name_native="x",
            occupations=["Director", "Storyboard"],
            gender="Female",
            age=42,
            date_of_birth=PartialDate(year=1980),
            years_active=[2000],
            home_town="Tokyo",
            language="Japanese",
            image_url="https://x.invalid/s.jpg",
            description="d",
            favourites=1,
            source=src,
        ).model_dump_json()
    )
    Studio.model_validate_json(
        Studio(id="_st", name="x", is_animation_studio=True, favourites=10, source=src).model_dump_json()
    )
    return True
