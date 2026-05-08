"""
``animedex api trace`` raw passthrough.

Backend: Trace.moe (api.trace.moe).

Rate limit: anonymous tier concurrency 1, quota 100/month.

--- LLM Agent Guidance ---
Two paths:

* ``GET /me`` reports the caller's quota state
  (``{id, priority, concurrency, quota, quotaUsed}``); free, no
  quota cost.
* ``GET /search?url=<encoded>&anilistInfo`` searches for a
  screenshot anime match. Each call consumes one from the monthly
  quota.
* ``POST /search`` with raw image bytes is also supported and is
  the only POST allowed by the read-only firewall on this backend.

Errors: HTTP 402 (quota exhausted), 429 (concurrency exceeded),
503 (backend overload), 403 (target image fetch failed).

``quotaUsed`` is returned as a string in the response; downstream
mappers must coerce.
--- End ---
"""

from __future__ import annotations

from typing import Dict, Optional

from animedex.api._dispatch import call as _dispatch_call
from animedex.api._envelope import RawResponse


def call(
    path: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[dict] = None,
    raw_body: Optional[bytes] = None,
    no_cache: bool = False,
    cache_ttl: Optional[int] = None,
    rate: str = "normal",
    follow_redirects: bool = True,
    user_agent: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    cache=None,
    session=None,
    rate_limit_registry=None,
    config=None,
) -> RawResponse:
    """Issue a Trace.moe request and return its envelope."""
    return _dispatch_call(
        backend="trace",
        path=path,
        method=method,
        headers=headers,
        params=params,
        raw_body=raw_body,
        no_cache=no_cache,
        cache_ttl=cache_ttl,
        rate=rate,
        follow_redirects=follow_redirects,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        cache=cache,
        session=session,
        rate_limit_registry=rate_limit_registry,
        config=config,
    )


def selftest() -> bool:
    """Smoke-test the Trace.moe passthrough (firewall + signature)."""
    from animedex.api._dispatch import selftest_backend_shim

    return selftest_backend_shim("trace", call, extra_params=("path", "method", "raw_body"))
