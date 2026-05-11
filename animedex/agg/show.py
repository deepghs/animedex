"""Single-source aggregate entity show."""

from __future__ import annotations

from typing import Optional

from animedex.agg._prefix_id import parse
from animedex.agg._type_routes import call_show_route, show_route_for, validate_entity_type
from animedex.config import Config
from animedex.models.common import ApiError


def show(type: str, prefix_id: str, *, config: Optional[Config] = None, **kw):
    """Show one entity from the backend encoded by ``prefix_id``.

    :param type: Entity type.
    :type type: str
    :param prefix_id: Prefix-encoded backend ID.
    :type prefix_id: str
    :param config: Optional config.
    :type config: Config or None
    :return: Backend-rich result.
    :rtype: object
    :raises ApiError: When the prefix or type/backend pair is invalid.
    """
    entity_type = validate_entity_type(type)
    parsed = parse(prefix_id)
    route = show_route_for(entity_type, parsed.backend)
    return call_show_route(route, parsed.id, config=config, **kw)


def selftest() -> bool:
    """Smoke-test show validation without network access.

    :return: ``True`` on success.
    :rtype: bool
    """
    try:
        show("publisher", "anilist:1")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover
        raise AssertionError("unsupported show accepted")
    return True
