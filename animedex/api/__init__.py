"""
``animedex api`` raw passthrough.

This package wires the 12 backends behind a single :func:`call`
dispatcher whose return value is the
:class:`~animedex.api._envelope.RawResponse` envelope. The CLI
renderers in :mod:`animedex.render.raw` project that envelope into
four output modes (default body / -i / -I / --debug).

The package is import-safe: it does not load backend modules eagerly.
"""

from animedex.api._envelope import (
    RawCacheInfo,
    RawRedirectHop,
    RawRequest,
    RawResponse,
    RawTiming,
    redact_credential_value,
    redact_headers,
)

__all__ = [
    "RawCacheInfo",
    "RawRedirectHop",
    "RawRequest",
    "RawResponse",
    "RawTiming",
    "redact_credential_value",
    "redact_headers",
]
