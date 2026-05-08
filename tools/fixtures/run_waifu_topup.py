"""Top-up Waifu.im fixtures (anonymous extras + auth /users/me).

Designed to run behind an HTTPS proxy when the upstream's Cloudflare
front-end has IP-blocked the bare-runner host. Picks up
``HTTPS_PROXY`` / ``HTTP_PROXY`` from the environment via
:mod:`requests`'s default proxy handling.

Pacing: 2.0 s between calls (serial; never concurrent). Overwrite is
disabled, so an existing fixture stops the script from re-issuing.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlencode

from tools.fixtures.capture import capture


BASE = "https://api.waifu.im"
PACE = 2.0


SEARCH_PROBES = (
    ("page-2", {"pageNumber": 2, "pageSize": 3}),
    ("orderby-uploaded-at", {"orderBy": "UPLOADED_AT", "pageSize": 3}),
    ("included-multiple-tags", {"included_tags": "waifu", "is_nsfw": "false", "pageSize": 3}),
    ("animated-false", {"isAnimated": "false", "pageSize": 2}),
    ("orientation-portrait", {"orientation": "PORTRAIT", "pageSize": 2}),
    ("min-width", {"width": ">1500", "pageSize": 2}),
)


def _waifu_apikey() -> str:
    key = os.environ.get("ANIMEDEX_WAIFU_TOKEN", "")
    if not key:
        raise SystemExit("ANIMEDEX_WAIFU_TOKEN must be set")
    return key


def main() -> int:
    total = 0

    print("-- Waifu.im /users/me (auth, X-Api-Key)")
    capture(
        backend="waifu",
        path_slug="users_me",
        label="default",
        method="GET",
        url=f"{BASE}/users/me",
        headers={"X-Api-Key": _waifu_apikey()},
        pace_seconds=PACE,
    )
    total += 1
    print("  waifu users_me: ok")

    print("-- Additional /images probes")
    for label, params in SEARCH_PROBES:
        url = f"{BASE}/images" + (f"?{urlencode(params)}" if params else "")
        capture(backend="waifu", path_slug="images", label=label, method="GET", url=url, pace_seconds=PACE)
        total += 1
        print(f"  /images {label}: ok")

    print("-- /tags page-2")
    capture(
        backend="waifu",
        path_slug="tags",
        label="page-2",
        method="GET",
        url=f"{BASE}/tags?pageNumber=2&pageSize=5",
        pace_seconds=PACE,
    )
    total += 1
    print("  /tags page-2: ok")

    print("-- /artists pages 2 + 3")
    for n in (2, 3):
        capture(
            backend="waifu",
            path_slug="artists",
            label=f"page-{n}",
            method="GET",
            url=f"{BASE}/artists?pageNumber={n}&pageSize=5",
            pace_seconds=PACE,
        )
        total += 1
        print(f"  /artists page-{n}: ok")

    print(f"Done: {total} fixtures captured (or skipped if already present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
