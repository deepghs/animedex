"""
Capture Waifu.im fixtures.

Hits the three JSON-emitting endpoints (``/tags`` / ``/images`` /
``/artists``) with enough variants for the high-level test suite to
exercise both default-SFW and explicit-NSFW paths plus single-tag /
multi-tag filtering.

Pacing: upstream cap not formally published; 1.5 s between calls is
visibly polite (~0.66 r/s, well under the project transport's 10 r/s
ceiling).
"""

from __future__ import annotations

import sys
from urllib.parse import urlencode

from tools.fixtures.capture import capture


BASE = "https://api.waifu.im"
PACE = 1.5


SEARCH_PROBES = (
    ("default-page1", {}),
    ("included-waifu", {"included_tags": "waifu"}),
    ("included-waifu-page-size-3", {"included_tags": "waifu", "pageSize": 3}),
    ("nsfw-true", {"isNsfw": "true", "pageSize": 3}),
    ("animated-true", {"isAnimated": "true", "pageSize": 2}),
    ("excluded-ero", {"excluded_tags": "ero", "pageSize": 3}),
)


def main() -> int:
    total = 0

    print("-- /tags (1 fixture)")
    capture(backend="waifu", path_slug="tags", label="all", method="GET",
            url=f"{BASE}/tags", pace_seconds=PACE)
    total += 1

    print("-- /tags/{id} + /tags/by-slug/{slug} (2 fixtures)")
    capture(backend="waifu", path_slug="tags_by_id", label="id-12-waifu", method="GET",
            url=f"{BASE}/tags/12", pace_seconds=PACE)
    capture(backend="waifu", path_slug="tags_by_slug", label="slug-waifu", method="GET",
            url=f"{BASE}/tags/by-slug/waifu", pace_seconds=PACE)
    total += 2

    print("-- /artists (1 fixture)")
    capture(backend="waifu", path_slug="artists", label="page-1", method="GET",
            url=f"{BASE}/artists", pace_seconds=PACE)
    total += 1

    print("-- /artists/{id} + /artists/by-name/{name} (2 fixtures)")
    capture(backend="waifu", path_slug="artists_by_id", label="id-80-gongha", method="GET",
            url=f"{BASE}/artists/80", pace_seconds=PACE)
    capture(backend="waifu", path_slug="artists_by_name", label="name-gongha", method="GET",
            url=f"{BASE}/artists/by-name/GongHa", pace_seconds=PACE)
    total += 2

    print(f"-- /images ({len(SEARCH_PROBES)} fixtures)")
    for i, (label, params) in enumerate(SEARCH_PROBES, 1):
        url = f"{BASE}/images" + (f"?{urlencode(params)}" if params else "")
        capture(backend="waifu", path_slug="images", label=label, method="GET",
                url=url, pace_seconds=PACE)
        total += 1
        print(f"  [{i:02d}/{len(SEARCH_PROBES)}] /images {label}")

    print("-- /images/{id} (1 fixture)")
    capture(backend="waifu", path_slug="images_by_id", label="id-1914", method="GET",
            url=f"{BASE}/images/1914", pace_seconds=PACE)
    total += 1

    print("-- /stats/public (1 fixture)")
    capture(backend="waifu", path_slug="stats_public", label="all", method="GET",
            url=f"{BASE}/stats/public", pace_seconds=PACE)
    total += 1

    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
