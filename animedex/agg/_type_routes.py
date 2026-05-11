"""Entity type routing for aggregate search/show."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional

from animedex.config import Config
from animedex.models.common import ApiError


ENTITY_TYPES = ("anime", "manga", "character", "person", "studio", "publisher")


@dataclass(frozen=True)
class SearchRoute:
    """One backend search route for an entity type."""

    backend: str
    function_name: str
    query_arg: str = "q"
    limit_arg: Optional[str] = None
    all_items: bool = False


@dataclass(frozen=True)
class ShowRoute:
    """One backend show route for an entity type."""

    backend: str
    function_name: str
    id_arg: str


_SEARCH_ROUTES: Dict[str, tuple[SearchRoute, ...]] = {
    "anime": (
        SearchRoute("anilist", "search", limit_arg="per_page"),
        SearchRoute("ann", "search"),
        SearchRoute("jikan", "search", limit_arg="limit"),
        SearchRoute("kitsu", "search", limit_arg="limit"),
        SearchRoute("shikimori", "search", limit_arg="limit"),
    ),
    "manga": (
        SearchRoute("anilist", "manga_search", limit_arg="per_page"),
        SearchRoute("jikan", "manga_search", limit_arg="limit"),
        SearchRoute("kitsu", "manga_search", limit_arg="limit"),
        SearchRoute("mangadex", "search", query_arg="title", limit_arg="limit"),
        SearchRoute("shikimori", "manga_search", limit_arg="limit"),
    ),
    "character": (
        SearchRoute("anilist", "character_search", limit_arg="per_page"),
        SearchRoute("jikan", "character_search", limit_arg="limit"),
        SearchRoute("kitsu", "character_search", limit_arg="limit"),
        SearchRoute("shikimori", "character_search", limit_arg="limit"),
    ),
    "person": (
        SearchRoute("anilist", "staff_search", limit_arg="per_page"),
        SearchRoute("jikan", "person_search", limit_arg="limit"),
        SearchRoute("kitsu", "person_search", limit_arg="limit"),
        SearchRoute("shikimori", "people_search", limit_arg="limit"),
    ),
    "studio": (
        SearchRoute("anilist", "studio_search", limit_arg="per_page"),
        SearchRoute("jikan", "producer_search", limit_arg="limit"),
        SearchRoute("kitsu", "producers", limit_arg="limit", all_items=True),
        SearchRoute("shikimori", "studios", all_items=True),
    ),
    "publisher": (SearchRoute("shikimori", "publishers", all_items=True),),
}


_SHOW_ROUTES: Dict[str, Dict[str, ShowRoute]] = {
    "anime": {
        "anilist": ShowRoute("anilist", "show", "id"),
        "ann": ShowRoute("ann", "show", "anime_id"),
        "jikan": ShowRoute("jikan", "show", "mal_id"),
        "kitsu": ShowRoute("kitsu", "show", "id"),
        "shikimori": ShowRoute("shikimori", "show", "anime_id"),
    },
    "manga": {
        "anilist": ShowRoute("anilist", "show", "id"),
        "jikan": ShowRoute("jikan", "manga_show", "mal_id"),
        "kitsu": ShowRoute("kitsu", "manga_show", "id"),
        "mangadex": ShowRoute("mangadex", "show", "id"),
        "shikimori": ShowRoute("shikimori", "manga_show", "manga_id"),
    },
    "character": {
        "anilist": ShowRoute("anilist", "character", "id"),
        "jikan": ShowRoute("jikan", "character_show", "mal_id"),
        "kitsu": ShowRoute("kitsu", "character", "id"),
        "shikimori": ShowRoute("shikimori", "character", "character_id"),
    },
    "person": {
        "anilist": ShowRoute("anilist", "staff", "id"),
        "jikan": ShowRoute("jikan", "person_show", "mal_id"),
        "kitsu": ShowRoute("kitsu", "person", "id"),
        "shikimori": ShowRoute("shikimori", "person", "person_id"),
    },
    "studio": {
        "anilist": ShowRoute("anilist", "studio", "id"),
        "jikan": ShowRoute("jikan", "producer_show", "mal_id"),
        "kitsu": ShowRoute("kitsu", "producer", "id"),
        "shikimori": ShowRoute("shikimori", "studio", "studio_id"),
    },
    "publisher": {"shikimori": ShowRoute("shikimori", "publisher", "publisher_id")},
}


def validate_entity_type(entity_type: str) -> str:
    """Validate and normalise an entity type.

    :param entity_type: User-supplied entity type.
    :type entity_type: str
    :return: Normalised type.
    :rtype: str
    :raises ApiError: When the type is unknown.
    """
    value = entity_type.lower()
    if value not in ENTITY_TYPES:
        raise ApiError(
            f"unknown type {entity_type!r}; supported types: {', '.join(ENTITY_TYPES)}",
            backend="aggregate",
            reason="bad-args",
        )
    return value


def search_routes_for(entity_type: str) -> tuple[SearchRoute, ...]:
    """Return search routes for ``entity_type``.

    :param entity_type: Normalised entity type.
    :type entity_type: str
    :return: Search routes.
    :rtype: tuple[SearchRoute, ...]
    """
    return _SEARCH_ROUTES[validate_entity_type(entity_type)]


def show_route_for(entity_type: str, backend: str) -> ShowRoute:
    """Return show route for an entity type/backend pair.

    :param entity_type: Entity type.
    :type entity_type: str
    :param backend: Backend name.
    :type backend: str
    :return: Show route.
    :rtype: ShowRoute
    :raises ApiError: When the pair is unsupported.
    """
    entity_type = validate_entity_type(entity_type)
    routes = _SHOW_ROUTES[entity_type]
    route = routes.get(backend)
    if route is None:
        supported = ", ".join(sorted(routes)) or "none"
        raise ApiError(
            f"type {entity_type!r} is not supported by backend {backend!r}; supported backends: {supported}",
            backend=backend,
            reason="bad-args",
        )
    return route


def backends_for_type(entity_type: str) -> Iterable[str]:
    """Return default fan-out backends for ``entity_type``.

    :param entity_type: Entity type.
    :type entity_type: str
    :return: Backend names in fan-out order.
    :rtype: iterable[str]
    """
    return tuple(route.backend for route in search_routes_for(entity_type))


def import_backend(backend: str):
    """Import a backend module by short name.

    :param backend: Backend name.
    :type backend: str
    :return: Imported module.
    :rtype: module
    """
    import importlib

    return importlib.import_module(f"animedex.backends.{backend}")


def call_search_route(route: SearchRoute, query: str, limit: int, *, config: Optional[Config] = None, **kw):
    """Call a search route.

    :param route: Search route.
    :type route: SearchRoute
    :param query: Search query.
    :type query: str
    :param limit: Per-source limit.
    :type limit: int
    :param config: Optional config.
    :type config: Config or None
    :return: Backend result list.
    :rtype: list
    """
    fn: Callable = getattr(import_backend(route.backend), route.function_name)
    kwargs = dict(kw)
    if route.all_items:
        rows = fn(config=config, **kwargs)
    else:
        kwargs[route.query_arg] = query
        if route.limit_arg:
            kwargs[route.limit_arg] = limit
        rows = fn(config=config, **kwargs)
    if route.backend == "ann" and hasattr(rows, "anime"):
        rows = rows.anime
    rows = list(rows)
    if route.all_items:
        rows = _filter_rows(rows, query)
        rows = rows[:limit]
    return rows


def call_show_route(route: ShowRoute, raw_id: str, *, config: Optional[Config] = None, **kw):
    """Call a show route.

    :param route: Show route.
    :type route: ShowRoute
    :param raw_id: Backend-native ID string.
    :type raw_id: str
    :param config: Optional config.
    :type config: Config or None
    :return: Backend result.
    :rtype: object
    """
    fn: Callable = getattr(import_backend(route.backend), route.function_name)
    value = raw_id if route.backend == "mangadex" else int(raw_id)
    return fn(config=config, **{route.id_arg: value}, **kw)


def _filter_rows(rows: list, query: str) -> list:
    needle = query.casefold()
    if not needle:
        return rows
    out = []
    for row in rows:
        dumped = row.model_dump(mode="json", by_alias=True) if hasattr(row, "model_dump") else row
        text = " ".join(str(value) for value in _walk_values(dumped))
        if needle in text.casefold():
            out.append(row)
    return out


def _walk_values(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _walk_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_values(value)
    elif obj is not None:
        yield obj


def selftest() -> bool:
    """Smoke-test entity type routing.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert "anilist" in set(backends_for_type("anime"))
    assert show_route_for("anime", "jikan").function_name == "show"
    try:
        show_route_for("publisher", "anilist")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover
        raise AssertionError("unsupported pair accepted")
    return True
