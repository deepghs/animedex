"""Rich AniList dataclasses (one per Query root we surface).

the high-level backend layer: every anonymous Query root field on AniList's GraphQL schema
gets a typed pydantic dataclass here. Core entities (Media, Character,
Staff, Studio) carry ``to_common()`` projections onto the cross-source
types in :mod:`animedex.models`. Long-tail entities (MediaTrend,
AiringSchedule, Review, Recommendation, Thread, ThreadComment,
Activity, MediaList, MediaListCollection, Following, Follower,
SiteStatistics, ExternalLinkSourceCollection, MediaTagCollection,
GenreCollection) expose their own typed shape but do not have a
common projection — they are AniList-specific concepts.

All models inherit :class:`~animedex.models.common.AnimedexModel`
(immutable, ``extra='ignore'``) so unknown upstream fields are dropped
silently and round-trip through JSON cleanly.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional

from animedex.models.anime import (
    AiringScheduleRow,
    Anime,
    AnimeRating,
    AnimeStreamingLink,
    AnimeTitle,
    NextAiringEpisode,
)
from animedex.models.character import Character, Staff, Studio
from animedex.models.common import BackendRichModel, PartialDate, SourceTag


# ---------- helper structs ----------


class _AnilistTitle(BackendRichModel):
    """AniList ``title`` block as returned by GraphQL.

    AniList allows any of the three locales to be ``null``; the
    common projection (:class:`AnimeTitle`) requires ``romaji``, so
    the mapper falls back to ``english`` or ``native`` when needed.
    """

    romaji: Optional[str] = None
    english: Optional[str] = None
    native: Optional[str] = None


class _AnilistName(BackendRichModel):
    """AniList ``name`` block (Character / Staff)."""

    full: Optional[str] = None
    native: Optional[str] = None
    alternative: List[str] = []


class _AnilistImage(BackendRichModel):
    """AniList ``image`` block (Character / Staff)."""

    large: Optional[str] = None
    medium: Optional[str] = None


class _AnilistCoverImage(BackendRichModel):
    """AniList ``coverImage`` block (Media)."""

    extraLarge: Optional[str] = None
    large: Optional[str] = None
    medium: Optional[str] = None
    color: Optional[str] = None


class _AnilistFuzzyDate(BackendRichModel):
    """AniList ``FuzzyDate`` block; matches :class:`PartialDate`."""

    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    def to_partial(self) -> Optional[PartialDate]:
        """Project to common :class:`PartialDate`. ``None`` when all
        three components are unknown."""
        if self.year is None and self.month is None and self.day is None:
            return None
        return PartialDate(year=self.year, month=self.month, day=self.day)

    def to_date(self) -> Optional[date]:
        """Best-effort projection to :class:`datetime.date` (returns
        ``None`` when the year is missing). Missing month/day default
        to ``1``."""
        if self.year is None:
            return None
        return date(self.year, self.month or 1, self.day or 1)


class _AnilistTrailer(BackendRichModel):
    """AniList ``trailer`` block."""

    id: Optional[str] = None
    site: Optional[str] = None
    thumbnail: Optional[str] = None

    def to_url(self) -> Optional[str]:
        """Compose a trailer landing URL from id + site."""
        if not self.id or not self.site:
            return None
        if self.site.lower() == "youtube":
            return f"https://www.youtube.com/watch?v={self.id}"
        if self.site.lower() == "dailymotion":
            return f"https://www.dailymotion.com/video/{self.id}"
        return None


class _AnilistTag(BackendRichModel):
    """AniList ``tag`` block (with rank)."""

    name: str
    rank: Optional[int] = None


class _AnilistStudioNode(BackendRichModel):
    """Inner studio node from ``Media.studios.edges[].node``."""

    id: Optional[int] = None
    name: str
    isAnimationStudio: Optional[bool] = None


class _AnilistStudioEdge(BackendRichModel):
    """Edge wrapper around a studio node, carrying ``isMain``."""

    isMain: Optional[bool] = None
    node: _AnilistStudioNode


class _AnilistStudioConnection(BackendRichModel):
    """``Media.studios`` connection."""

    edges: List[_AnilistStudioEdge] = []


class _AnilistNextAiringEpisode(BackendRichModel):
    """``Media.nextAiringEpisode`` block."""

    airingAt: int  # epoch seconds
    timeUntilAiring: int
    episode: int

    def to_common(self) -> NextAiringEpisode:
        return NextAiringEpisode(
            airing_at=datetime.fromtimestamp(self.airingAt, tz=timezone.utc),
            time_until_airing_seconds=self.timeUntilAiring,
            episode=self.episode,
        )


class _AnilistExternalLink(BackendRichModel):
    """``Media.externalLinks[]`` entry."""

    id: Optional[int] = None
    site: str
    type: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None


class _AnilistStreamingEpisode(BackendRichModel):
    """``Media.streamingEpisodes[]`` entry."""

    title: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None
    site: Optional[str] = None


class _AnilistMediaCharacterEdge(BackendRichModel):
    """``Character.media.edges[]`` entry — what role this character
    plays in which media."""

    characterRole: Optional[str] = None
    node: Optional[dict] = None  # leave as raw dict; the role string is what matters


class _AnilistMediaCharacterConnection(BackendRichModel):
    edges: List[_AnilistMediaCharacterEdge] = []


# ---------- core entity dataclasses ----------


class AnilistAnime(BackendRichModel):
    """Full AniList Media (anime / manga) record.

    Field-for-field projection of the
    :data:`~animedex.backends.anilist._queries.Q_MEDIA_BY_ID`
    response. ``to_common()`` projects onto the cross-source
    :class:`~animedex.models.anime.Anime`.
    """

    id: int
    idMal: Optional[int] = None
    title: _AnilistTitle = _AnilistTitle()
    synonyms: List[str] = []
    type: Optional[str] = None  # ANIME / MANGA
    format: Optional[str] = None
    status: Optional[str] = None
    episodes: Optional[int] = None
    duration: Optional[int] = None
    season: Optional[str] = None
    seasonYear: Optional[int] = None
    startDate: Optional[_AnilistFuzzyDate] = None
    endDate: Optional[_AnilistFuzzyDate] = None
    genres: List[str] = []
    tags: List[_AnilistTag] = []
    averageScore: Optional[int] = None
    meanScore: Optional[int] = None
    popularity: Optional[int] = None
    favourites: Optional[int] = None
    trending: Optional[int] = None
    isAdult: Optional[bool] = None
    countryOfOrigin: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    coverImage: Optional[_AnilistCoverImage] = None
    bannerImage: Optional[str] = None
    trailer: Optional[_AnilistTrailer] = None
    studios: Optional[_AnilistStudioConnection] = None
    nextAiringEpisode: Optional[_AnilistNextAiringEpisode] = None
    externalLinks: List[_AnilistExternalLink] = []
    streamingEpisodes: List[_AnilistStreamingEpisode] = []
    source_tag: SourceTag

    def to_common(self) -> Anime:
        """Project onto the cross-source :class:`Anime`."""
        # Title: AniList allows all three locales null; the common
        # projection requires ``romaji``. Fall back to english/native
        # if romaji is empty.
        romaji = self.title.romaji or self.title.english or self.title.native or ""
        common_title = AnimeTitle(romaji=romaji, english=self.title.english, native=self.title.native)

        score = None
        if self.averageScore is not None:
            score = AnimeRating(score=float(self.averageScore), scale=100.0)

        # Status normalisation
        status_map = {
            "RELEASING": "airing",
            "FINISHED": "finished",
            "NOT_YET_RELEASED": "upcoming",
            "CANCELLED": "cancelled",
            "HIATUS": "hiatus",
        }
        status = status_map.get((self.status or "").upper(), "unknown") if self.status else None

        # Format passes through; AniList vocabulary == Anime model
        # vocabulary
        anime_format = (
            self.format if self.format in ("TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC") else None
        )

        season = self.season if self.season in ("WINTER", "SPRING", "SUMMER", "FALL") else None

        studios: List[str] = []
        if self.studios is not None:
            studios = [edge.node.name for edge in self.studios.edges]

        # Streaming: use externalLinks (type=STREAMING) plus
        # streamingEpisodes (dedupe by site).
        streaming_links: List[AnimeStreamingLink] = []
        seen_providers = set()
        for ext in self.externalLinks or []:
            if (ext.type or "").upper() == "STREAMING" and ext.url and ext.site:
                if ext.site not in seen_providers:
                    streaming_links.append(AnimeStreamingLink(provider=ext.site, url=ext.url))
                    seen_providers.add(ext.site)
        for se in self.streamingEpisodes or []:
            if se.site and se.url and se.site not in seen_providers:
                streaming_links.append(AnimeStreamingLink(provider=se.site, url=se.url))
                seen_providers.add(se.site)

        next_ep = self.nextAiringEpisode.to_common() if self.nextAiringEpisode is not None else None

        ids = {"anilist": str(self.id)}
        if self.idMal is not None:
            ids["mal"] = str(self.idMal)

        return Anime(
            id=f"anilist:{self.id}",
            title=common_title,
            score=score,
            episodes=self.episodes,
            studios=studios,
            streaming=streaming_links,
            description=self.description,
            genres=list(self.genres),
            tags=[t.name for t in (self.tags or [])],
            status=status,
            format=anime_format,
            season=season,
            season_year=self.seasonYear,
            aired_from=self.startDate.to_date() if self.startDate else None,
            aired_to=self.endDate.to_date() if self.endDate else None,
            duration_minutes=self.duration,
            cover_image_url=(self.coverImage.large if self.coverImage else None),
            banner_image_url=self.bannerImage,
            trailer_url=(self.trailer.to_url() if self.trailer else None),
            source_material=(self.source.lower() if self.source else None),
            country_of_origin=self.countryOfOrigin,
            is_adult=self.isAdult,
            title_synonyms=list(self.synonyms),
            popularity=self.popularity,
            favourites=self.favourites,
            trending=self.trending,
            next_airing_episode=next_ep,
            ids=ids,
            source=self.source_tag,
        )


class AnilistCharacter(BackendRichModel):
    """Full AniList Character record."""

    id: int
    name: _AnilistName = _AnilistName()
    image: Optional[_AnilistImage] = None
    description: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None  # AniList sometimes returns "55" or composite
    dateOfBirth: Optional[_AnilistFuzzyDate] = None
    bloodType: Optional[str] = None
    favourites: Optional[int] = None
    media: Optional[_AnilistMediaCharacterConnection] = None
    source_tag: SourceTag

    def to_common(self) -> Character:
        # Pick MAIN role first if available.
        role = None
        if self.media is not None:
            for edge in self.media.edges:
                if edge.characterRole == "MAIN":
                    role = "MAIN"
                    break
            if role is None and self.media.edges:
                role = self.media.edges[0].characterRole

        return Character(
            id=f"anilist:char:{self.id}",
            name=self.name.full or self.name.native or "(unknown)",
            name_native=self.name.native,
            name_alternatives=list(self.name.alternative),
            role=role,
            image_url=(self.image.large if self.image else None),
            description=self.description,
            gender=self.gender,
            age=self.age,
            date_of_birth=(self.dateOfBirth.to_partial() if self.dateOfBirth else None),
            favourites=self.favourites,
            source=self.source_tag,
        )


class AnilistStaff(BackendRichModel):
    """Full AniList Staff record."""

    id: int
    name: _AnilistName = _AnilistName()
    image: Optional[_AnilistImage] = None
    description: Optional[str] = None
    primaryOccupations: List[str] = []
    gender: Optional[str] = None
    age: Optional[int] = None
    dateOfBirth: Optional[_AnilistFuzzyDate] = None
    yearsActive: List[int] = []
    homeTown: Optional[str] = None
    languageV2: Optional[str] = None
    favourites: Optional[int] = None
    source_tag: SourceTag

    def to_common(self) -> Staff:
        return Staff(
            id=f"anilist:staff:{self.id}",
            name=self.name.full or self.name.native or "(unknown)",
            name_native=self.name.native,
            occupations=list(self.primaryOccupations),
            gender=self.gender,
            age=self.age,
            date_of_birth=(self.dateOfBirth.to_partial() if self.dateOfBirth else None),
            years_active=list(self.yearsActive),
            home_town=self.homeTown,
            language=self.languageV2,
            image_url=(self.image.large if self.image else None),
            description=self.description,
            favourites=self.favourites,
            source=self.source_tag,
        )


class AnilistStudio(BackendRichModel):
    """Full AniList Studio record."""

    id: int
    name: str
    isAnimationStudio: Optional[bool] = None
    favourites: Optional[int] = None
    source_tag: SourceTag

    def to_common(self) -> Studio:
        return Studio(
            id=f"anilist:studio:{self.id}",
            name=self.name,
            is_animation_studio=self.isAnimationStudio,
            favourites=self.favourites,
            source=self.source_tag,
        )


# ---------- long-tail entity dataclasses ----------


class AnilistMediaTrend(BackendRichModel):
    """One row from :data:`Q_MEDIA_TREND` — daily trending stats."""

    mediaId: Optional[int] = None
    date: int  # epoch seconds
    trending: Optional[int] = None
    averageScore: Optional[int] = None
    popularity: Optional[int] = None
    inProgress: Optional[int] = None
    episode: Optional[int] = None
    source_tag: SourceTag


class AnilistAiringSchedule(BackendRichModel):
    """One row from :data:`Q_AIRING_SCHEDULE`."""

    id: int
    airingAt: int
    episode: int
    timeUntilAiring: int
    media_id: Optional[int] = None
    media_title_romaji: Optional[str] = None
    source_tag: SourceTag

    def to_common(self) -> AiringScheduleRow:
        """Project onto the common airing schedule row."""
        return AiringScheduleRow(
            title=self.media_title_romaji or f"AniList media {self.media_id or self.id}",
            airing_at=datetime.fromtimestamp(self.airingAt, tz=timezone.utc),
            episode=self.episode,
            source=self.source_tag,
        )


class AnilistReview(BackendRichModel):
    """One row from :data:`Q_REVIEW`."""

    id: int
    summary: Optional[str] = None
    score: Optional[int] = None
    rating: Optional[int] = None
    ratingAmount: Optional[int] = None
    user_name: Optional[str] = None
    siteUrl: Optional[str] = None
    source_tag: SourceTag


class AnilistRecommendation(BackendRichModel):
    """One row from :data:`Q_RECOMMENDATION`."""

    id: int
    rating: Optional[int] = None
    media_id: Optional[int] = None
    media_title: Optional[str] = None
    recommendation_id: Optional[int] = None
    recommendation_title: Optional[str] = None
    source_tag: SourceTag


class AnilistThread(BackendRichModel):
    """One row from :data:`Q_THREAD`."""

    id: int
    title: Optional[str] = None
    body: Optional[str] = None
    user_name: Optional[str] = None
    replyCount: Optional[int] = None
    viewCount: Optional[int] = None
    createdAt: Optional[int] = None
    source_tag: SourceTag


class AnilistThreadComment(BackendRichModel):
    """One row from :data:`Q_THREAD_COMMENT`."""

    id: int
    comment: Optional[str] = None
    user_name: Optional[str] = None
    createdAt: Optional[int] = None
    source_tag: SourceTag


class AnilistActivity(BackendRichModel):
    """One row from :data:`Q_ACTIVITY` (TextActivity / ListActivity)."""

    id: int
    kind: str  # "text" or "list"
    text: Optional[str] = None  # TextActivity
    status: Optional[str] = None  # ListActivity
    user_name: Optional[str] = None
    media_title: Optional[str] = None  # ListActivity
    createdAt: Optional[int] = None
    source_tag: SourceTag


class AnilistActivityReply(BackendRichModel):
    """One row from :data:`Q_ACTIVITY_REPLY`."""

    id: int
    text: Optional[str] = None
    user_name: Optional[str] = None
    createdAt: Optional[int] = None
    source_tag: SourceTag


class AnilistFollowEntry(BackendRichModel):
    """One follower / following entry."""

    id: int
    name: str
    source_tag: SourceTag


class AnilistMediaListEntry(BackendRichModel):
    """One row from :data:`Q_MEDIA_LIST_PUBLIC`."""

    id: int
    status: Optional[str] = None
    score: Optional[float] = None
    progress: Optional[int] = None
    media_id: Optional[int] = None
    media_title: Optional[str] = None
    source_tag: SourceTag


class AnilistMediaListGroup(BackendRichModel):
    """One named list (e.g. ``Watching``) inside a collection."""

    name: str
    status: Optional[str] = None
    entry_count: int


class AnilistMediaListCollection(BackendRichModel):
    """One ``MediaListCollection`` block."""

    user_id: Optional[int] = None
    user_name: Optional[str] = None
    lists: List[AnilistMediaListGroup] = []
    source_tag: SourceTag


class AnilistGenreCollection(BackendRichModel):
    """``GenreCollection`` singleton."""

    genres: List[str] = []
    source_tag: SourceTag


class AnilistMediaTag(BackendRichModel):
    """One row from :data:`Q_MEDIA_TAG_COLLECTION`."""

    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    isAdult: Optional[bool] = None
    isGeneralSpoiler: Optional[bool] = None
    isMediaSpoiler: Optional[bool] = None
    source_tag: SourceTag


class AnilistSiteStatBucket(BackendRichModel):
    """One ``date / count / change`` triple from SiteStatistics."""

    date: int
    count: int
    change: int


class AnilistSiteStatistics(BackendRichModel):
    """``SiteStatistics`` snapshot."""

    users: List[AnilistSiteStatBucket] = []
    anime: List[AnilistSiteStatBucket] = []
    manga: List[AnilistSiteStatBucket] = []
    characters: List[AnilistSiteStatBucket] = []
    staff: List[AnilistSiteStatBucket] = []
    reviews: List[AnilistSiteStatBucket] = []
    source_tag: SourceTag


class AnilistExternalLinkSource(BackendRichModel):
    """One entry from
    :data:`Q_EXTERNAL_LINK_SOURCE_COLLECTION`."""

    id: int
    site: str
    type: Optional[str] = None
    icon: Optional[str] = None
    language: Optional[str] = None
    source_tag: SourceTag


class AnilistUserStatistics(BackendRichModel):
    """User profile statistics block."""

    anime_count: Optional[int] = None
    anime_mean_score: Optional[float] = None
    anime_minutes_watched: Optional[int] = None
    manga_count: Optional[int] = None
    manga_mean_score: Optional[float] = None
    manga_chapters_read: Optional[int] = None


class AnilistUser(BackendRichModel):
    """``User`` record."""

    id: int
    name: str
    about: Optional[str] = None
    avatar_large: Optional[str] = None
    siteUrl: Optional[str] = None
    statistics: Optional[AnilistUserStatistics] = None
    source_tag: SourceTag


class AnilistNotification(BackendRichModel):
    """One row from the authenticated ``Page.notifications`` query.

    AniList notifications are a polymorphic union (``AiringNotification``,
    ``FollowingNotification``, ``ActivityMessageNotification``, etc.).
    The kind is identified by GraphQL fragment; this model carries the
    common subset plus a ``kind`` discriminator so consumers can branch.
    """

    id: int
    kind: str  # short-hand: "airing" / "following" / "activity-message" / ...
    type: Optional[str] = None  # AniList's full enum string
    contexts: List[str] = []
    context: Optional[str] = None
    user_name: Optional[str] = None
    createdAt: Optional[int] = None
    source_tag: SourceTag


class AnilistMarkdown(BackendRichModel):
    """Result of the authenticated ``Markdown`` query — rendered HTML.

    AniList renders its in-house markdown to HTML server-side. This is
    the typed wrapper around the ``html`` field.
    """

    html: str
    source_tag: SourceTag


class AnilistAniChartUser(BackendRichModel):
    """Authenticated ``AniChartUser`` snapshot.

    AniChart is a sister project of AniList. ``settings`` and
    ``highlights`` are AniList-encoded JSON strings the user's
    AniChart profile page reads; we surface them verbatim and let the
    consumer decode them on demand.
    """

    user_id: int
    user_name: str
    settings: dict = {}
    highlights: dict = {}
    source_tag: SourceTag


def selftest() -> bool:
    """Smoke-test the AniList rich dataclasses by round-tripping a
    minimally-populated instance of each through pydantic."""
    src = SourceTag(backend="anilist", fetched_at=datetime.now(timezone.utc))
    AnilistAnime.model_validate_json(
        AnilistAnime(id=1, title=_AnilistTitle(romaji="x"), source_tag=src).model_dump_json()
    )
    AnilistCharacter.model_validate_json(
        AnilistCharacter(id=1, name=_AnilistName(full="x"), source_tag=src).model_dump_json()
    )
    AnilistStaff.model_validate_json(AnilistStaff(id=1, name=_AnilistName(full="x"), source_tag=src).model_dump_json())
    AnilistStudio.model_validate_json(AnilistStudio(id=1, name="x", source_tag=src).model_dump_json())
    AnilistMediaTrend.model_validate_json(AnilistMediaTrend(date=0, source_tag=src).model_dump_json())
    AnilistAiringSchedule.model_validate_json(
        AnilistAiringSchedule(id=1, airingAt=0, episode=1, timeUntilAiring=0, source_tag=src).model_dump_json()
    )
    AnilistReview.model_validate_json(AnilistReview(id=1, source_tag=src).model_dump_json())
    AnilistRecommendation.model_validate_json(AnilistRecommendation(id=1, source_tag=src).model_dump_json())
    AnilistThread.model_validate_json(AnilistThread(id=1, source_tag=src).model_dump_json())
    AnilistThreadComment.model_validate_json(AnilistThreadComment(id=1, source_tag=src).model_dump_json())
    AnilistActivity.model_validate_json(AnilistActivity(id=1, kind="text", source_tag=src).model_dump_json())
    AnilistActivityReply.model_validate_json(AnilistActivityReply(id=1, source_tag=src).model_dump_json())
    AnilistFollowEntry.model_validate_json(AnilistFollowEntry(id=1, name="x", source_tag=src).model_dump_json())
    AnilistMediaListEntry.model_validate_json(AnilistMediaListEntry(id=1, source_tag=src).model_dump_json())
    AnilistMediaListCollection.model_validate_json(AnilistMediaListCollection(source_tag=src).model_dump_json())
    AnilistGenreCollection.model_validate_json(AnilistGenreCollection(source_tag=src).model_dump_json())
    AnilistMediaTag.model_validate_json(AnilistMediaTag(id=1, name="x", source_tag=src).model_dump_json())
    AnilistSiteStatistics.model_validate_json(AnilistSiteStatistics(source_tag=src).model_dump_json())
    AnilistExternalLinkSource.model_validate_json(
        AnilistExternalLinkSource(id=1, site="x", source_tag=src).model_dump_json()
    )
    AnilistUser.model_validate_json(AnilistUser(id=1, name="x", source_tag=src).model_dump_json())
    AnilistNotification.model_validate_json(AnilistNotification(id=1, kind="airing", source_tag=src).model_dump_json())
    AnilistMarkdown.model_validate_json(AnilistMarkdown(html="<p>x</p>", source_tag=src).model_dump_json())
    AnilistAniChartUser.model_validate_json(
        AnilistAniChartUser(user_id=1, user_name="x", source_tag=src).model_dump_json()
    )
    return True
