"""MangaDex OAuth2 helper.

MangaDex's authenticated endpoints sit behind a Keycloak-fronted
OAuth2 password grant (the ``client_credentials`` flow is *not*
enabled for personal API clients). Every call needs:

* ``client_id`` / ``client_secret`` from the caller's
  https://mangadex.org/settings → API Clients page;
* ``username`` / ``password`` for the caller's MangaDex account.

This module exchanges those four for a short-lived ``access_token``
(15 min lifetime) and caches the result in process memory so a
session of authenticated calls does not re-hit the auth endpoint per
request. The cache is keyed on ``client_id``; calling code never
sees the password again after the first exchange.

The token endpoint is a different host
(``auth.mangadex.org``) than the API host (``api.mangadex.org``);
it's hit directly via :mod:`requests` rather than through the
project dispatcher to keep the auth flow off the api-host's rate
limit bucket.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests

from animedex.config import Config
from animedex.models.common import ApiError
from animedex.transport.useragent import compose_user_agent


_TOKEN_URL = "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token"
_REFRESH_LEEWAY_SEC = 30  # refresh this many seconds before the upstream's expiry

# Module-level cache, keyed on client_id (per-account).
_TOKEN_CACHE: Dict[str, "_CachedToken"] = {}


@dataclass(frozen=True)
class MangaDexCredentials:
    """The four-tuple needed for OAuth2 password grant.

    :ivar client_id: Personal API client identifier.
    :vartype client_id: str
    :ivar client_secret: Personal API client secret.
    :vartype client_secret: str
    :ivar username: MangaDex account username.
    :vartype username: str
    :ivar password: MangaDex account password.
    :vartype password: str
    """

    client_id: str
    client_secret: str
    username: str
    password: str

    def __repr__(self) -> str:
        """Return a representation that does not leak secrets."""
        return (
            f"MangaDexCredentials(client_id={self.client_id!r}, "
            f"client_secret=***, username={self.username!r}, password=***)"
        )

    @classmethod
    def from_string(cls, raw: str) -> "MangaDexCredentials":
        """Parse the colon-separated quad
        ``client_id:client_secret:username:password``.

        :param raw: The packed credential string.
        :type raw: str
        :return: Parsed credentials.
        :rtype: MangaDexCredentials
        :raises ApiError: When the string does not have exactly four
                            colon-separated parts.
        """
        parts = raw.split(":", 3)
        if len(parts) != 4:
            raise ApiError(
                "mangadex credentials must be 'client_id:client_secret:username:password'",
                backend="mangadex",
                reason="bad-args",
            )
        return cls(*parts)


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # epoch seconds


def _auth_session() -> requests.Session:
    """Build the direct-auth session with project transport headers.

    The OAuth token endpoint intentionally avoids the main dispatcher
    so it does not consume the api-host rate-limit bucket, but it still
    honours the repository-wide wire contracts for User-Agent and Via.

    :return: Session prepared for Keycloak token requests.
    :rtype: requests.Session
    """
    session = requests.Session()
    session.headers.update({"User-Agent": compose_user_agent(None)})
    session.headers.pop("Via", None)
    return session


def _redact_auth_error_body(body: str) -> str:
    """Mask credential-like fields in a Keycloak error snippet.

    :param body: Response text snippet.
    :type body: str
    :return: Redacted text safe for an :class:`ApiError` message.
    :rtype: str
    """
    return re.sub(r"(?i)(password|client_secret)=([^&\s]+)", r"\1=***", body)


def resolve_credentials(
    creds: Optional[object] = None,
    *,
    config: Optional[Config] = None,
) -> MangaDexCredentials:
    """Locate a usable :class:`MangaDexCredentials` quad.

    ``creds`` accepts either a pre-built :class:`MangaDexCredentials`
    instance or the same colon-separated string the env var uses
    (``client_id:client_secret:username:password``). The CLI threads
    ``--creds`` through as a string.

    Resolution order (first hit wins):

    1. The explicit ``creds`` argument.
    2. The ``ANIMEDEX_MANGADEX_CREDS`` environment variable.
    3. The :class:`~animedex.auth.store.TokenStore` attached to
       ``config`` (looked up under the key ``"mangadex"``).

    :param creds: Optional pre-built credentials.
    :type creds: MangaDexCredentials, str, or None
    :param config: Optional :class:`~animedex.config.Config`.
    :type config: Config or None
    :return: Resolved credentials.
    :rtype: MangaDexCredentials
    :raises ApiError: When none of the three sources yield a value.
    """
    if creds is not None:
        if isinstance(creds, MangaDexCredentials):
            return creds
        if isinstance(creds, str):
            return MangaDexCredentials.from_string(creds)
        raise ApiError(
            "mangadex creds= must be MangaDexCredentials or 'client_id:client_secret:username:password' string",
            backend="mangadex",
            reason="bad-args",
        )
    env = os.environ.get("ANIMEDEX_MANGADEX_CREDS")
    if env:
        return MangaDexCredentials.from_string(env)
    if config is not None:
        store = config.effective_token_store()
        stored = store.get("mangadex")
        if stored:
            return MangaDexCredentials.from_string(stored)
    raise ApiError(
        "mangadex auth required: pass creds=, set ANIMEDEX_MANGADEX_CREDS, "
        "or store 'client_id:client_secret:username:password' under 'mangadex' "
        "in the token store",
        backend="mangadex",
        reason="auth-required",
    )


def get_bearer_token(
    creds: Optional[object] = None,
    *,
    config: Optional[Config] = None,
    force_refresh: bool = False,
) -> str:
    """Return a usable Bearer access token, exchanging credentials
    for a fresh one when the cache is empty or stale.

    :param creds: Explicit credentials (overrides env / store).
    :type creds: MangaDexCredentials or None
    :param config: Optional :class:`~animedex.config.Config` used to
                    resolve credentials from the token store.
    :type config: Config or None
    :param force_refresh: When ``True``, ignore the in-memory cache
                           and run the OAuth exchange again.
    :type force_refresh: bool
    :return: Bearer access token (no ``Bearer`` prefix).
    :rtype: str
    :raises ApiError: ``auth-required`` when no credentials resolve;
                        ``upstream-error`` on Keycloak failures;
                        ``upstream-decode`` on a malformed response.
    """
    resolved = resolve_credentials(creds, config=config)
    cached = _TOKEN_CACHE.get(resolved.client_id)
    now = time.time()
    if not force_refresh and cached and cached.expires_at - _REFRESH_LEEWAY_SEC > now:
        return cached.access_token

    try:
        r = _auth_session().post(
            _TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": resolved.client_id,
                "client_secret": resolved.client_secret,
                "username": resolved.username,
                "password": resolved.password,
            },
            timeout=30.0,
        )
    except requests.RequestException as exc:
        raise ApiError(f"mangadex auth network error: {exc}", backend="mangadex", reason="upstream-error") from exc

    if r.status_code != 200:
        error_body = _redact_auth_error_body(r.text[:200])
        raise ApiError(
            f"mangadex auth returned {r.status_code}: {error_body}",
            backend="mangadex",
            reason="auth-required" if r.status_code in (400, 401) else "upstream-error",
        )

    try:
        body = r.json()
    except ValueError as exc:
        raise ApiError(f"mangadex auth returned non-JSON: {exc}", backend="mangadex", reason="upstream-decode") from exc

    token = body.get("access_token")
    if not token:
        raise ApiError("mangadex auth response missing access_token", backend="mangadex", reason="upstream-shape")
    expires_in = body.get("expires_in")
    if expires_in is None:
        raise ApiError("mangadex auth response missing expires_in", backend="mangadex", reason="upstream-shape")
    _TOKEN_CACHE[resolved.client_id] = _CachedToken(access_token=token, expires_at=now + float(expires_in))
    return token


def selftest() -> bool:
    """Smoke-test the credential parser. The OAuth exchange is not
    triggered because it requires a network round-trip; the helper
    is exercised by the per-endpoint live capture / replay path.

    :return: ``True`` on success; raises on schema drift.
    :rtype: bool
    """
    creds = MangaDexCredentials.from_string("a:b:c:d")
    assert creds.client_id == "a"
    assert creds.client_secret == "b"
    assert creds.username == "c"
    assert creds.password == "d"
    try:
        MangaDexCredentials.from_string("only-three:parts:here")
    except ApiError as exc:
        assert exc.reason == "bad-args"
    else:  # pragma: no cover - defensive
        raise AssertionError("expected ApiError on malformed creds")
    return True
