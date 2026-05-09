"""
Four output renderers for :class:`~animedex.api._envelope.RawResponse`.

Per #3 §5.0:

* :func:`render_body` - default, body text only (gh api equivalent).
* :func:`render_include` - ``-i``, curl-style status + headers + body.
* :func:`render_head` - ``-I``, status + headers only.
* :func:`render_debug` - ``--debug``, structured JSON envelope.

The CLI in :mod:`animedex.entry.cli` picks one of these based on the
mutually-exclusive output flags.
"""

from __future__ import annotations

import base64
import json
from typing import Optional

from animedex.api._envelope import RawResponse


_DEBUG_BODY_CAP_BYTES = 65536  # 64 KiB default truncation in --debug


def render_body(envelope: RawResponse) -> str:
    """Default mode: print the response body as text.

    Returns ``body_text`` when it decoded as UTF-8; otherwise base64-
    encodes ``body_bytes`` so the output is still printable. Callers
    that need the raw bytes for binary content should use the
    library API (``animedex.api.call``) instead of the CLI.

    :param envelope: The response envelope.
    :type envelope: RawResponse
    :return: Body text (or base64-encoded bytes when not decodable).
    :rtype: str
    """
    if envelope.firewall_rejected is not None:
        return envelope.firewall_rejected.get("message", "")
    if envelope.body_text is not None:
        return envelope.body_text
    return base64.b64encode(envelope.body_bytes).decode("ascii")


def _format_status_line(envelope: RawResponse) -> str:
    if envelope.firewall_rejected is not None:
        reason = envelope.firewall_rejected.get("reason", "rejected")
        return f"HTTP/0 0 firewall-rejected ({reason})"
    return f"HTTP/1.1 {envelope.status}"


def _format_headers_block(envelope: RawResponse) -> str:
    lines = []
    for name, value in envelope.response_headers.items():
        lines.append(f"{name}: {value}")
    return "\n".join(lines)


def render_include(envelope: RawResponse) -> str:
    """``-i`` mode: status line + response headers + blank + body.

    Mirrors ``curl -i`` output. The header block uses the response's
    own header casing as captured.

    :param envelope: The response envelope.
    :type envelope: RawResponse
    :return: Status + headers + body, separated by blank line.
    :rtype: str
    """
    status_line = _format_status_line(envelope)
    headers_block = _format_headers_block(envelope)
    body = render_body(envelope)
    return f"{status_line}\n{headers_block}\n\n{body}"


def render_head(envelope: RawResponse) -> str:
    """``-I`` mode: status line + response headers, no body.

    :param envelope: The response envelope.
    :type envelope: RawResponse
    :return: Status + headers.
    :rtype: str
    """
    status_line = _format_status_line(envelope)
    headers_block = _format_headers_block(envelope)
    return f"{status_line}\n{headers_block}"


def render_debug(envelope: RawResponse, *, full_body: bool = False) -> str:
    """``--debug`` mode: structured JSON envelope.

    Emits the entire :class:`RawResponse` as indented JSON. Body
    content is truncated to :data:`_DEBUG_BODY_CAP_BYTES` (64 KiB) by
    default and tagged with ``body_truncated_at_bytes``; pass
    ``full_body=True`` to emit the full body verbatim. Binary bodies
    that did not decode as UTF-8 are base64-encoded inside the JSON.

    Credential headers in ``request.headers`` are already redacted by
    the dispatcher (see :func:`animedex.api._envelope.redact_headers`);
    this renderer does not perform additional redaction.

    :param envelope: The response envelope.
    :type envelope: RawResponse
    :param full_body: When ``True``, do not truncate the body.
    :type full_body: bool
    :return: Indented JSON of the envelope.
    :rtype: str
    """
    payload = envelope.model_dump(mode="json")

    # Body handling: when the body decoded as UTF-8 we have body_text;
    # otherwise body_bytes is base64-encoded by pydantic's bytes
    # serialization (which is what model_dump emits for bytes fields).
    body_text: Optional[str] = payload.get("body_text")
    if body_text is not None and not full_body and len(body_text) > _DEBUG_BODY_CAP_BYTES:
        payload["body_text"] = body_text[:_DEBUG_BODY_CAP_BYTES]
        payload["body_truncated_at_bytes"] = _DEBUG_BODY_CAP_BYTES
    elif body_text is None and not full_body:
        # Binary body: model_dump renders bytes as base64; cap the
        # base64 string accordingly (cap reflects encoded length, not
        # original byte length, but it bounds the JSON output size
        # which is what matters for stdout safety).
        b64 = payload.get("body_bytes", "")
        if isinstance(b64, str) and len(b64) > _DEBUG_BODY_CAP_BYTES:
            payload["body_bytes"] = b64[:_DEBUG_BODY_CAP_BYTES]
            payload["body_truncated_at_bytes"] = _DEBUG_BODY_CAP_BYTES

    return json.dumps(payload, indent=2, ensure_ascii=False)


def selftest() -> bool:
    """Smoke-test the four renderers.

    :return: ``True`` on success.
    :rtype: bool
    """
    from animedex.api._envelope import (
        RawCacheInfo,
        RawRequest,
        RawResponse as _RR,
        RawTiming,
    )

    env = _RR(
        backend="_selftest",
        request=RawRequest(method="GET", url="https://x.invalid/", headers={"User-Agent": "x"}),
        status=200,
        response_headers={"Content-Type": "application/json"},
        body_bytes=b'{"ok":true}',
        body_text='{"ok":true}',
        timing=RawTiming(total_ms=1.0, rate_limit_wait_ms=0, request_ms=1.0),
        cache=RawCacheInfo(hit=False),
    )

    assert render_body(env) == '{"ok":true}'
    assert "200" in render_include(env)
    assert "200" in render_head(env)
    assert json.loads(render_debug(env))["status"] == 200
    return True
