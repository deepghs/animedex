"""Rich ANN Encyclopedia dataclasses.

ANN's public encyclopedia API is XML-only. The high-level backend
parses XML into a generic node tree first, then validates the
backend-specific rich models below. A 200 response carrying
``<warning>...`` is an empty-result signal and is preserved on the
rich response models instead of being raised as an error.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import Field

from animedex.models.anime import Anime, AnimeTitle
from animedex.models.character import Character, Staff
from animedex.models.common import BackendRichModel, SourceTag
from animedex.render.xml import ATTRS_KEY, CHILDREN_BY_TAG_KEY, CHILDREN_KEY, TAG_KEY, TAIL_KEY, TEXT_KEY


class AnnXmlNode(BackendRichModel):
    """A lossless XML node produced by :mod:`animedex.render.xml`."""

    tag: str = Field(alias=TAG_KEY)
    attrs: Dict[str, str] = Field(default_factory=dict, alias=ATTRS_KEY)
    text: Optional[str] = Field(default=None, alias=TEXT_KEY)
    tail: Optional[str] = Field(default=None, alias=TAIL_KEY)
    children: List["AnnXmlNode"] = Field(default_factory=list, alias=CHILDREN_KEY)
    children_by_tag: Dict[str, List["AnnXmlNode"]] = Field(default_factory=dict, alias=CHILDREN_BY_TAG_KEY)

    @classmethod
    def from_adapter(cls, node: Dict[str, Any]) -> "AnnXmlNode":
        """Build an :class:`AnnXmlNode` from the generic XML adapter shape."""
        return cls.model_validate(node)

    def by_tag(self, tag: str) -> List["AnnXmlNode"]:
        """Return child nodes with ``tag`` from the grouped index."""
        return list(self.children_by_tag.get(tag) or [])

    def first_text(self, tag: str) -> Optional[str]:
        """Return text from the first direct child named ``tag``."""
        rows = self.by_tag(tag)
        return rows[0].text if rows else None


class AnnInfo(BackendRichModel):
    """One ANN ``<info>`` node."""

    attrs: Dict[str, str] = {}
    text: Optional[str] = None
    children: List[AnnXmlNode] = []

    @property
    def type(self) -> Optional[str]:
        """Return the ANN info type, such as ``"Main title"``."""
        return self.attrs.get("type")


class AnnPersonRef(BackendRichModel):
    """A referenced ANN person from staff or cast rows."""

    id: Optional[str] = None
    name: Optional[str] = None

    def to_common_staff(self, source_tag: Optional[SourceTag], occupations: Optional[List[str]] = None) -> Staff:
        """Project the person reference onto :class:`~animedex.models.character.Staff`."""
        return Staff(
            id=f"ann:person:{self.id or self.name or 'unknown'}",
            name=self.name or "",
            occupations=occupations or [],
            source=source_tag or _default_src(),
        )


class AnnCompanyRef(BackendRichModel):
    """A referenced ANN company from credit rows."""

    id: Optional[str] = None
    name: Optional[str] = None


class AnnStaff(BackendRichModel):
    """One ANN ``<staff>`` row."""

    attrs: Dict[str, str] = {}
    task: Optional[str] = None
    person: Optional[AnnPersonRef] = None

    def to_common(self, source_tag: Optional[SourceTag] = None) -> Staff:
        """Project this staff credit onto the common staff shape."""
        person = self.person or AnnPersonRef()
        occupations = [self.task] if self.task else []
        return person.to_common_staff(source_tag, occupations)


class AnnCast(BackendRichModel):
    """One ANN ``<cast>`` row."""

    attrs: Dict[str, str] = {}
    role: Optional[str] = None
    person: Optional[AnnPersonRef] = None

    def to_common(self, source_tag: Optional[SourceTag] = None) -> Character:
        """Project the cast row onto a character role record."""
        return Character(
            id=f"ann:character:{self.role or 'unknown'}",
            name=self.role or "",
            role=self.attrs.get("lang"),
            source=source_tag or _default_src(),
        )


class AnnCredit(BackendRichModel):
    """One ANN ``<credit>`` row."""

    attrs: Dict[str, str] = {}
    task: Optional[str] = None
    company: Optional[AnnCompanyRef] = None


class AnnLink(BackendRichModel):
    """A small text + href record from review, news, release, or website rows."""

    attrs: Dict[str, str] = {}
    text: Optional[str] = None


class AnnEpisode(BackendRichModel):
    """One ANN ``<episode>`` row."""

    attrs: Dict[str, str] = {}
    titles: List[AnnInfo] = []


class AnnRelation(BackendRichModel):
    """One related ANN encyclopedia entry."""

    direction: str
    attrs: Dict[str, str] = {}


class AnnAnime(BackendRichModel):
    """One ANN ``<anime>`` encyclopedia entry."""

    id: str
    gid: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    precision: Optional[str] = None
    generated_on: Optional[str] = None
    info: List[AnnInfo] = []
    staff: List[AnnStaff] = []
    cast: List[AnnCast] = []
    credits: List[AnnCredit] = []
    episodes: List[AnnEpisode] = []
    reviews: List[AnnLink] = []
    releases: List[AnnLink] = []
    news: List[AnnLink] = []
    relations: List[AnnRelation] = []
    raw: AnnXmlNode
    source_tag: Optional[SourceTag] = None

    def info_by_type(self, type_name: str) -> List[AnnInfo]:
        """Return ``<info>`` rows matching an ANN type string."""
        return [row for row in self.info if row.type == type_name]

    def first_info_text(self, type_name: str) -> Optional[str]:
        """Return text from the first matching ``<info>`` row."""
        rows = self.info_by_type(type_name)
        return rows[0].text if rows else None

    def to_common(self) -> Anime:
        """Project this ANN entry onto :class:`~animedex.models.anime.Anime`."""
        title = self.first_info_text("Main title") or self.name or ""
        native = None
        synonyms = []
        for row in self.info_by_type("Alternative title"):
            if row.text:
                synonyms.append(row.text)
                if native is None and row.attrs.get("lang") == "JA":
                    native = row.text
        genres = [row.text for row in self.info_by_type("Genres") if row.text]
        themes = [row.text for row in self.info_by_type("Themes") if row.text]
        picture = self.info_by_type("Picture")
        cover_url = picture[0].attrs.get("src") if picture else None
        return Anime(
            id=f"ann:{self.id}",
            title=AnimeTitle(romaji=title, english=title, native=native),
            episodes=_parse_optional_int(self.first_info_text("Number of episodes")),
            studios=[credit.company.name for credit in self.credits if credit.company and credit.company.name],
            description=self.first_info_text("Plot Summary"),
            genres=genres,
            tags=themes,
            format=_normalise_format(self.type),
            aired_from=_parse_vintage_start(self.first_info_text("Vintage")),
            cover_image_url=cover_url,
            age_rating=self.first_info_text("Objectionable content"),
            title_synonyms=synonyms,
            ids={"ann": self.id},
            source=self.source_tag or _default_src(),
        )


class AnnAnimeResponse(BackendRichModel):
    """ANN ``api.xml`` response containing anime entries and warnings."""

    warnings: List[str] = []
    anime: List[AnnAnime] = []
    raw: AnnXmlNode
    source_tag: Optional[SourceTag] = None


class AnnReportItem(BackendRichModel):
    """One row from ``reports.xml``."""

    fields: Dict[str, Any] = {}
    raw: AnnXmlNode
    source_tag: Optional[SourceTag] = None


class AnnReport(BackendRichModel):
    """ANN ``reports.xml`` response."""

    attrs: Dict[str, str] = {}
    args: Dict[str, str] = {}
    items: List[AnnReportItem] = []
    warnings: List[str] = []
    raw: AnnXmlNode
    source_tag: Optional[SourceTag] = None


def _default_src() -> SourceTag:
    """Construct a fallback :class:`SourceTag` for direct model use."""
    from datetime import datetime, timezone

    return SourceTag(backend="ann", fetched_at=datetime.now(timezone.utc))


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_vintage_start(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    first = value.split(" to ", 1)[0].strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            if fmt == "%Y":
                return date(int(first), 1, 1)
            if fmt == "%Y-%m":
                year, month = [int(part) for part in first.split("-", 1)]
                return date(year, month, 1)
            year, month, day = [int(part) for part in first.split("-", 2)]
            return date(year, month, day)
        except (TypeError, ValueError):
            continue
    return None


def _normalise_format(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    norm = value.upper().replace(" ", "_")
    if norm in {"TV", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"}:
        return norm
    return None


def _info_from_node(node: AnnXmlNode) -> AnnInfo:
    return AnnInfo(attrs=node.attrs, text=node.text, children=node.children)


def _link_from_node(node: AnnXmlNode) -> AnnLink:
    return AnnLink(attrs=node.attrs, text=node.text)


def _person_from_node(node: Optional[AnnXmlNode]) -> Optional[AnnPersonRef]:
    if node is None:
        return None
    return AnnPersonRef(id=node.attrs.get("id"), name=node.text)


def _company_from_node(node: Optional[AnnXmlNode]) -> Optional[AnnCompanyRef]:
    if node is None:
        return None
    return AnnCompanyRef(id=node.attrs.get("id"), name=node.text)


def _first(nodes: List[AnnXmlNode]) -> Optional[AnnXmlNode]:
    return nodes[0] if nodes else None


def anime_from_node(node: AnnXmlNode, source_tag: SourceTag) -> AnnAnime:
    """Build :class:`AnnAnime` from an adapted XML ``anime`` node."""
    info = [_info_from_node(row) for row in node.by_tag("info")]
    staff = [
        AnnStaff(attrs=row.attrs, task=row.first_text("task"), person=_person_from_node(_first(row.by_tag("person"))))
        for row in node.by_tag("staff")
    ]
    cast = [
        AnnCast(attrs=row.attrs, role=row.first_text("role"), person=_person_from_node(_first(row.by_tag("person"))))
        for row in node.by_tag("cast")
    ]
    credits = [
        AnnCredit(
            attrs=row.attrs,
            task=row.first_text("task"),
            company=_company_from_node(_first(row.by_tag("company"))),
        )
        for row in node.by_tag("credit")
    ]
    episodes = [
        AnnEpisode(attrs=row.attrs, titles=[_info_from_node(t) for t in row.by_tag("title")])
        for row in node.by_tag("episode")
    ]
    relations = [
        *(AnnRelation(direction="prev", attrs=row.attrs) for row in node.by_tag("related-prev")),
        *(AnnRelation(direction="next", attrs=row.attrs) for row in node.by_tag("related-next")),
    ]
    return AnnAnime.model_validate(
        {
            "id": node.attrs.get("id"),
            "gid": node.attrs.get("gid"),
            "type": node.attrs.get("type"),
            "name": node.attrs.get("name"),
            "precision": node.attrs.get("precision"),
            "generated_on": node.attrs.get("generated-on"),
            "info": info,
            "staff": staff,
            "cast": cast,
            "credits": credits,
            "episodes": episodes,
            "reviews": [_link_from_node(row) for row in node.by_tag("review")],
            "releases": [_link_from_node(row) for row in node.by_tag("release")],
            "news": [_link_from_node(row) for row in node.by_tag("news")],
            "relations": relations,
            "raw": node,
            "source_tag": source_tag,
        }
    )


def anime_response_from_root(root: AnnXmlNode, source_tag: SourceTag) -> AnnAnimeResponse:
    """Build an :class:`AnnAnimeResponse` from an ANN ``<ann>`` root."""
    warnings = [row.text for row in root.by_tag("warning") if row.text]
    anime = [anime_from_node(row, source_tag) for row in root.by_tag("anime")]
    return AnnAnimeResponse(warnings=warnings, anime=anime, raw=root, source_tag=source_tag)


def report_from_root(root: AnnXmlNode, source_tag: SourceTag) -> AnnReport:
    """Build an :class:`AnnReport` from a ``<report>`` root."""
    args = {}
    for args_node in root.by_tag("args"):
        for child in args_node.children:
            args[child.tag] = child.text or ""
    items = []
    for item in root.by_tag("item"):
        fields = {child.tag: child.text for child in item.children}
        items.append(AnnReportItem(fields=fields, raw=item, source_tag=source_tag))
    warnings = [row.text for row in root.by_tag("warning") if row.text]
    return AnnReport(attrs=root.attrs, args=args, items=items, warnings=warnings, raw=root, source_tag=source_tag)


def selftest() -> bool:
    """Smoke-test the ANN rich models and warning path."""
    from datetime import datetime, timezone

    src = SourceTag(backend="ann", fetched_at=datetime.now(timezone.utc))
    raw = AnnXmlNode.from_adapter(
        {
            "_tag": "ann",
            "_attrs": {},
            "_children": [
                {"_tag": "warning", "_attrs": {}, "_text": "no result", "_children": [], "_children_by_tag": {}}
            ],
            "_children_by_tag": {
                "warning": [
                    {"_tag": "warning", "_attrs": {}, "_text": "no result", "_children": [], "_children_by_tag": {}}
                ]
            },
        }
    )
    response = anime_response_from_root(raw, src)
    assert response.warnings == ["no result"]
    anime = AnnAnime(
        id="1",
        name="Angel Links",
        type="TV",
        info=[AnnInfo(attrs={"type": "Main title", "lang": "EN"}, text="Angel Links")],
        raw=raw,
        source_tag=src,
    )
    assert anime.to_common().id == "ann:1"
    return True
