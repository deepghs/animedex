"""
User-Agent string composition for animedex HTTP requests.

The transport injects a minimal project-identifying User-Agent on
every outgoing request unless the caller passes their own. The
default form is ``animedex/<version>`` with no contact suffix; this
was decided in #3's Phase 1 exploration after live-testing all 8
backends - every one accepts the bare ``animedex/<version>`` form,
so the verbose ``animedex/<v> (+<email>)`` shape that earlier code
shipped was over-engineered.

Two backends genuinely require *some* non-empty UA at the wire
(MangaDex returns 400 on empty; Danbooru's Cloudflare front returns
a challenge HTML on empty). The other six accept any value
including empty. Our default satisfies all eight.

A caller that needs a different UA - identifying their own bot,
testing what an upstream does with empty/spoofed values, or any
other reason - can pass ``custom`` to :func:`compose_user_agent`.
We do not police caller intent; per the Human Agency Principle
(``AGENTS.md §0``) explicit caller choices win over project defaults.
"""

from __future__ import annotations

from typing import Optional


def default_user_agent() -> str:
    """Compose the project-default User-Agent string.

    Reads :mod:`animedex.config.meta` so the version stays in sync
    with the package metadata. The resulting string is a bare
    ``name/version`` form (e.g. ``"animedex/0.0.1"``) - no parens,
    no contact suffix, no descriptors. Every backend we target
    accepts this form on the wire.

    :return: User-Agent string for animedex's own requests.
    :rtype: str
    """
    from animedex.config.meta import __TITLE__, __VERSION__

    return f"{__TITLE__}/{__VERSION__}"


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
    from animedex.config.meta import __TITLE__, __VERSION__

    ua = default_user_agent()
    assert ua == f"{__TITLE__}/{__VERSION__}"
    assert compose_user_agent("custom/1.0") == "custom/1.0"
    assert compose_user_agent(None) == ua
    assert compose_user_agent("") == ua
    return True
