"""Multi-source entity search."""

from __future__ import annotations

from typing import Optional

from animedex.agg._fanout import fanout, select_sources
from animedex.agg._prefix_id import prefix_for_backend
from animedex.agg._type_routes import call_search_route, search_routes_for, validate_entity_type
from animedex.config import Config
from animedex.models.aggregate import AggregateResult
from animedex.models.common import AnimedexModel, ApiError


def _native_id(row, backend: str):
    data = row.model_dump(mode="json", by_alias=True) if hasattr(row, "model_dump") else row
    if backend == "anilist":
        return data.get("id")
    if backend == "jikan":
        return data.get("mal_id")
    if backend in {"kitsu", "mangadex", "shikimori", "ann"}:
        return data.get("id")
    return data.get("id")


def _annotate_row(row, backend: str):
    update = {"_source": backend}
    prefix_id = prefix_for_backend(backend, _native_id(row, backend))
    if prefix_id is not None:
        update["_prefix_id"] = prefix_id
    if isinstance(row, AnimedexModel):
        return row.model_copy(update=update)
    data = dict(row)
    data.update(update)
    return data


def search(
    type: str,
    q: str,
    *,
    limit: int = 10,
    source: Optional[str] = None,
    config: Optional[Config] = None,
    **kw,
) -> AggregateResult:
    """Search an entity type across every supporting backend.

    :param type: Entity type: ``anime``, ``manga``, ``character``,
                 ``person``, ``studio``, or ``publisher``.
    :type type: str
    :param q: Search query, passed verbatim to each backend that
              supports a search endpoint.
    :type q: str
    :param limit: Per-source row cap.
    :type limit: int
    :param source: Optional comma-separated source allowlist.
    :type source: str or None
    :param config: Optional config.
    :type config: Config or None
    :return: Aggregate result envelope.
    :rtype: AggregateResult
    :raises ApiError: When the type or source list is invalid.
    """
    entity_type = validate_entity_type(type)
    if limit < 1:
        raise ApiError("limit must be >= 1", backend="aggregate", reason="bad-args")
    routes = search_routes_for(entity_type)
    selected = set(select_sources((route.backend for route in routes), source))
    selected_routes = [route for route in routes if route.backend in selected]

    def _make(route):
        return lambda: [
            _annotate_row(row, route.backend) for row in call_search_route(route, q, limit, config=config, **kw)
        ]

    return fanout({route.backend: _make(route) for route in selected_routes})


def selftest() -> bool:
    """Smoke-test search validation without network access.

    :return: ``True`` on success.
    :rtype: bool
    """
    try:
        search("badtype", "x")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover
        raise AssertionError("bad type accepted")
    return True
