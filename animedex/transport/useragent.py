"""
User-Agent string composition for animedex HTTP requests.

A single project-identifying User-Agent satisfies the mandatory
header policies of MangaDex, Shikimori, Danbooru, and AniDB
(``plans/02 §7``). Honesty is part of the contract: per the Danbooru
help page the UA must not pretend to be a browser, and the Shikimori
TOS rejects requests with no UA at all. This module is the *single*
source of truth for that string; the rest of the transport layer
calls in here.

The default UA includes the project name, version, and an honest
contact email pulled from :mod:`animedex.config.meta` so an upstream
sysadmin who needs to reach us can do so without scraping logs. A
caller that needs a different UA - typically a downstream Python
user wrapping animedex inside their own product - can override with
:func:`compose_user_agent`.
"""

from __future__ import annotations

from typing import Optional


def default_user_agent() -> str:
    """Compose the project-default User-Agent string.

    Reads :mod:`animedex.config.meta` so the version stays in sync
    with the package metadata. The resulting string carries the
    project name, version, and contact email in a simple
    ``name/version (+contact)`` form that every upstream we target
    accepts.

    :return: User-Agent string for animedex's own requests.
    :rtype: str
    """
    from animedex.config.meta import __AUTHOR_EMAIL__, __TITLE__, __VERSION__

    return f"{__TITLE__}/{__VERSION__} (+{__AUTHOR_EMAIL__})"


def compose_user_agent(custom: Optional[str]) -> str:
    """Pick the User-Agent for an outgoing request.

    Honours a non-empty caller-provided string verbatim, otherwise
    returns :func:`default_user_agent`. Empty strings collapse to the
    default rather than being passed through, so a misconfigured
    caller still satisfies the upstream's mandatory-UA contract.

    :param custom: Caller-supplied User-Agent, or ``None`` /``""``
                    to use the default.
    :type custom: str or None
    :return: User-Agent string to send on the wire.
    :rtype: str
    """
    if custom:
        return custom
    return default_user_agent()


def selftest() -> bool:
    """Smoke-test the User-Agent composer.

    Asserts the default string carries the project name, version, and
    contact email, and that an explicit override is honoured. Stays
    fully offline and finishes in microseconds so the diagnostic
    runner can include it on every CLI invocation.

    :return: ``True`` on success.
    :rtype: bool
    """
    from animedex.config.meta import __AUTHOR_EMAIL__, __TITLE__, __VERSION__

    ua = default_user_agent()
    assert __TITLE__ in ua
    assert __VERSION__ in ua
    assert __AUTHOR_EMAIL__ in ua
    assert compose_user_agent("custom/1.0") == "custom/1.0"
    assert compose_user_agent(None) == ua
    assert compose_user_agent("") == ua
    return True
