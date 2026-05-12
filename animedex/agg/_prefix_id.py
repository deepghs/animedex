"""Prefix-encoded entity references for aggregate commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from animedex.models.common import ApiError


_PREFIX_TO_BACKEND: Dict[str, str] = {
    "anilist": "anilist",
    "mal": "jikan",
    "myanimelist": "jikan",
    "jikan": "jikan",
    "kitsu": "kitsu",
    "shikimori": "shikimori",
    "mangadex": "mangadex",
    "ann": "ann",
    "animenewsnetwork": "ann",
}
_DEFERRED_PREFIXES: Set[str] = {"anidb"}
_NUMERIC_BACKENDS = {"anilist", "jikan", "kitsu", "shikimori", "ann"}
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


@dataclass(frozen=True)
class ParsedPrefixId:
    """Parsed ``prefix:id`` reference.

    :ivar prefix: User-supplied prefix, normalised to lower-case.
    :vartype prefix: str
    :ivar backend: Backend module name selected by the prefix.
    :vartype backend: str
    :ivar id: Backend-native ID string.
    :vartype id: str
    """

    prefix: str
    backend: str
    id: str


def known_prefixes() -> Iterable[str]:
    """Return the supported non-deferred prefixes.

    :return: Prefix names sorted for display.
    :rtype: iterable[str]
    """
    return tuple(sorted(_PREFIX_TO_BACKEND))


def parse(prefix_id: str) -> ParsedPrefixId:
    """Parse and validate a ``prefix:id`` reference.

    :param prefix_id: Reference such as ``"anilist:154587"``.
    :type prefix_id: str
    :return: Parsed reference.
    :rtype: ParsedPrefixId
    :raises ApiError: When the prefix or ID format is invalid.
    """
    if ":" not in prefix_id:
        raise ApiError(
            f"entity reference must be prefix:id, got {prefix_id!r}",
            backend="aggregate",
            reason="bad-args",
        )
    prefix, raw_id = prefix_id.split(":", 1)
    prefix = prefix.strip().lower()
    raw_id = raw_id.strip()
    if not prefix or not raw_id:
        raise ApiError("entity reference must include both prefix and id", backend="aggregate", reason="bad-args")
    if prefix in _DEFERRED_PREFIXES:
        raise ApiError(
            "anidb references are recognised but the AniDB high-level helpers are not shipped yet",
            backend="anidb",
            reason="auth-required",
        )
    backend = _PREFIX_TO_BACKEND.get(prefix)
    if backend is None:
        expected = ", ".join(sorted([*_PREFIX_TO_BACKEND, *_DEFERRED_PREFIXES]))
        raise ApiError(
            f"unknown prefix {prefix!r}; expected one of: {expected}", backend="aggregate", reason="bad-args"
        )
    validate_id(backend, raw_id)
    return ParsedPrefixId(prefix=prefix, backend=backend, id=raw_id)


def validate_id(backend: str, raw_id: str) -> None:
    """Validate backend-native ID format.

    :param backend: Backend module name.
    :type backend: str
    :param raw_id: Backend-native ID string.
    :type raw_id: str
    :raises ApiError: When ``raw_id`` is invalid for ``backend``.
    """
    if backend in _NUMERIC_BACKENDS:
        if not raw_id.isdigit():
            raise ApiError(
                f"ID is not numeric for backend {backend!r}: {raw_id!r}",
                backend=backend,
                reason="bad-args",
            )
    elif backend == "mangadex" and _UUID_RE.match(raw_id) is None:
        raise ApiError(
            f"ID is not a MangaDex UUID: {raw_id!r}",
            backend="mangadex",
            reason="bad-args",
        )


def prefix_for_backend(backend: str, native_id: object) -> Optional[str]:
    """Compose the canonical prefix ID for a backend-native ID.

    :param backend: Backend name.
    :type backend: str
    :param native_id: Backend-native ID value.
    :type native_id: object
    :return: ``prefix:id`` or ``None`` when no public prefix exists.
    :rtype: str or None
    """
    if native_id is None:
        return None
    if backend == "jikan":
        return f"mal:{native_id}"
    if backend in {"anilist", "kitsu", "shikimori", "mangadex", "ann"}:
        return f"{backend}:{native_id}"
    return None


def selftest() -> bool:
    """Smoke-test prefix parsing and validation.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert parse("mal:52991").backend == "jikan"
    assert parse("myanimelist:52991").backend == "jikan"
    assert parse("mangadex:dc8bbc4c-eb7a-4d27-b96a-9aa8c8db4adb").backend == "mangadex"
    assert prefix_for_backend("jikan", 52991) == "mal:52991"
    try:
        parse("anilist:abc")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover
        raise AssertionError("invalid numeric id accepted")
    return True
