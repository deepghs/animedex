"""
HTTP transport layer for animedex backends.

This package owns every wire-level concern that backend modules must
honour but should never have to reimplement: the User-Agent string
(:mod:`animedex.transport.useragent`), per-backend rate limiting
(:mod:`animedex.transport.ratelimit`), the read-only firewall
(:mod:`animedex.transport.read_only`), and the
:class:`~animedex.transport.http.HttpClient` wrapper that composes
them on top of :class:`requests.Session`.

Per ``plans/02`` the rate-limit caps and the User-Agent / Via header
contracts are hard P1 obligations: violating them gets the user
punished by a third party (4xx, ban, or worse). The transport layer
is therefore the one place in the codebase where these obligations
are configured; nothing outside transport should touch them.
"""
