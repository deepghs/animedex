"""
HTTP client wrapper used by every animedex backend.

The :class:`HttpClient` composes :mod:`animedex.transport.useragent`,
:mod:`animedex.transport.ratelimit`, and
:mod:`animedex.transport.read_only` on top of a single
``requests.Session``. Responsibilities:

* Inject the project User-Agent on every request unless the caller
  passes an explicit override.
* Strip ``Via`` from outgoing headers (MangaDex forbids it; we strip
  it for *every* backend to make the contract uniform and so a
  misconfigured shared proxy cannot accidentally trip the constraint).
* Consult the per-backend rate-limit bucket before issuing the call.
* Run the read-only firewall before the request leaves the host.

Backends should not subclass this class; they should compose it. The
goal is one HTTP call site per backend so retry, timeout, redirect
policy, and TLS settings live in exactly one place.
"""

from __future__ import annotations

from typing import Any, Optional

import requests

from animedex.transport.ratelimit import RateLimitRegistry, default_registry
from animedex.transport.read_only import enforce_read_only
from animedex.transport.useragent import compose_user_agent


class HttpClient:
    """A read-only HTTP client bound to a single backend.

    :param backend: Backend identifier (e.g. ``"anilist"``); used to
                     pick the rate-limit bucket and the read-only
                     ruleset.
    :type backend: str
    :param base_url: Base URL prefix joined with the request path.
    :type base_url: str
    :param session: Existing ``requests.Session`` to reuse.
                     Optional; one is created when not given.
    :type session: requests.Session or None
    :param rate_limit_registry: Source of the rate-limit bucket.
                                  Defaults to
                                  :func:`animedex.transport.ratelimit.default_registry`.
    :type rate_limit_registry: RateLimitRegistry or None
    :param user_agent: Override for the User-Agent string. Defaults
                        to :func:`animedex.transport.useragent.default_user_agent`.
    :type user_agent: str or None
    :param timeout_seconds: Request timeout in seconds.
    :type timeout_seconds: float
    """

    def __init__(
        self,
        *,
        backend: str,
        base_url: str,
        session: Optional[requests.Session] = None,
        rate_limit_registry: Optional[RateLimitRegistry] = None,
        user_agent: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.backend = backend
        self.base_url = base_url.rstrip("/")
        self.session = session if session is not None else requests.Session()
        self.rate_limit_registry = rate_limit_registry if rate_limit_registry is not None else default_registry()
        self.user_agent = compose_user_agent(user_agent)
        self.timeout_seconds = timeout_seconds

    def _join(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def _prepare_headers(self, extra_headers: Optional[dict]) -> dict:
        # Header policy:
        # - User-Agent: P1b (plan 02 §1, §7). Project default is injected;
        #   a caller-supplied User-Agent in extra_headers overrides it
        #   verbatim. We do not police caller intent here - if a caller
        #   passes "browser/x" they get "browser/x" on the wire, and
        #   Shikimori's 403 is their feedback. Same principle as
        #   `rating:e` queries elsewhere in the codebase.
        # - Via: P1a (plan 02 §7). MangaDex forbids this header; we strip
        #   it unconditionally regardless of caller intent because the
        #   request would otherwise fail outright.
        headers = {"User-Agent": self.user_agent}
        if extra_headers:
            for key, value in extra_headers.items():
                if key.lower() == "via":
                    continue
                headers[key] = value
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Issue an HTTP request through the read-only stack.

        :param method: HTTP method (case-insensitive on input;
                        upper-cased internally).
        :type method: str
        :param path: Request path. Joined with ``base_url`` unless an
                      absolute URL is given.
        :type path: str
        :param kwargs: Forwarded to :meth:`requests.Session.request`,
                        with ``headers`` mediated by
                        :meth:`_prepare_headers` and ``timeout``
                        defaulted to :attr:`timeout_seconds`.
        :return: The response object.
        :rtype: requests.Response
        :raises ApiError: When the read-only firewall rejects the
                           request, or when the rate-limit bucket
                           rejects the backend identifier.
        """
        method_up = method.upper()
        # The firewall expects the *path* relative to the backend
        # (e.g. AniList's GraphQL is rooted at "/"); pass `path` as
        # given so absolute URLs are not allowed to mask intent.
        firewall_path = path if path.startswith("/") else "/" + path
        enforce_read_only(self.backend, method_up, firewall_path)
        self.rate_limit_registry.get(self.backend).acquire()

        prepared_kwargs = dict(kwargs)
        prepared_kwargs["headers"] = self._prepare_headers(prepared_kwargs.get("headers"))
        prepared_kwargs.setdefault("timeout", self.timeout_seconds)

        return self.session.request(method_up, self._join(path), **prepared_kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """Issue a ``GET`` request. Convenience over :meth:`request`."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """Issue a ``POST`` request. Convenience over :meth:`request`.

        Subject to the per-backend ``POST`` rules in
        :mod:`animedex.transport.read_only`.
        """
        return self.request("POST", path, **kwargs)


def selftest() -> bool:
    """Smoke-test :class:`HttpClient` without touching the network.

    Verifies the constructor wires UA / firewall / rate limiter
    correctly, and that the firewall rejects a clear mutation before
    the request would have been issued. Avoids any real socket
    activity.

    :return: ``True`` on success.
    :rtype: bool
    """
    from animedex.models.common import ApiError

    client = HttpClient(backend="anilist", base_url="https://upstream.invalid")
    assert "animedex/" in client.user_agent

    try:
        client.request("DELETE", "/x")
    except ApiError as exc:
        assert exc.reason == "read-only"
    else:  # pragma: no cover - defensive selftest assertion
        raise AssertionError("DELETE should have been rejected by the firewall")
    return True
