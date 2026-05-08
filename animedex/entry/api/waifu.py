"""``animedex api waifu`` subcommand."""

from __future__ import annotations

from animedex.entry.api._get_only_template import make_get_only_subcommand


api_waifu = make_get_only_subcommand(
    name="waifu",
    backend_module_name="waifu",
    docstring="""Issue a Waifu.im GET request (anonymous; SFW + NSFW image API).

    PATH is the URL path on ``api.waifu.im``. The upstream's
    ``/images`` endpoint defaults to SFW only when ``isNsfw`` is
    omitted; pass ``isNsfw=true`` to opt in to NSFW results.

    \b
    Docs:
      https://docs.waifu.im/                            project docs index
      https://www.waifu.im/                              project home

    \b
    Common paths:
      /tags                                  list every tag with image counts
      /artists                               paginated artist directory
      /images                                paginated image listing (SFW only by default)
      /images?included_tags=waifu            filter by a single tag
      /images?included_tags=waifu&isNsfw=true   NSFW opt-in
      /images?isAnimated=true                GIF / animated subset

    \b
    Examples:
      animedex api waifu /tags
      animedex api waifu '/images?included_tags=waifu&pageSize=3'
      animedex api waifu '/images?isNsfw=true' -i
      animedex api waifu /images --debug | jq '.timing'
    \f

    Backend: Waifu.im (api.waifu.im).

    Rate limit: anonymous; not formally published (transport applies
    a 10 req/sec sustained ceiling with a 10-token burst budget).

    --- LLM Agent Guidance ---
    PATH is the URL path on api.waifu.im. Common reads:
    /tags (list every tag with image counts),
    /images?included_tags=...&excluded_tags=...&isNsfw=true|false
    (paginated images matching the filter). Upstream defaults
    isNsfw to false when omitted. When the user did not explicitly
    ask for NSFW content, omit the parameter. When they did, pass
    it through unmodified — the project's posture is to inform,
    not to gate.
    --- End ---
    """,
)
