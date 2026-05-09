"""Capture AnimeChan fixtures.

Captures the anonymous read endpoints documented for the free tier:
random quote, random by anime, random by character, paginated quotes by
anime, paginated quotes by character, and anime information by ID.

Pacing: AnimeChan's anonymous free tier is 5 req/hour. The default pace
is 65 seconds to stay visibly below that cap. If your local network path
is already rate-limited, set ``HTTP_PROXY`` / ``HTTPS_PROXY`` before
running the script; the proxy value is read by ``requests`` and is not
written to fixtures.
"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlencode

from tools.fixtures.capture import capture


BASE = "https://api.animechan.io/v1"


PROBES = (
    ("random", "random-fruits-basket", "/quotes/random", None),
    ("random_by_anime", "naruto", "/quotes/random", {"anime": "Naruto"}),
    ("random_by_character", "saitama", "/quotes/random", {"character": "Saitama"}),
    ("quotes_by_anime", "naruto-page-1", "/quotes", {"anime": "Naruto", "page": 1}),
    ("quotes_by_character", "saitama-page-1", "/quotes", {"character": "Saitama", "page": 1}),
    ("anime", "one-punch-man-188", "/anime/188", None),
)


def _url(path: str, params: dict | None) -> str:
    if not params:
        return f"{BASE}{path}"
    return f"{BASE}{path}?{urlencode(params)}"


def main(argv=None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Capture AnimeChan fixtures.")
    parser.add_argument("--pace", type=float, default=65.0, help="Seconds to sleep before each request.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing fixture labels.")
    args = parser.parse_args(argv)

    for i, (slug, label, path, params) in enumerate(PROBES, 1):
        print(f"[{i:02d}/{len(PROBES)}] {path} {label}")
        capture(
            backend="quote",
            path_slug=slug,
            label=label,
            method="GET",
            url=_url(path, params),
            pace_seconds=args.pace,
            overwrite=args.overwrite,
        )
    print(f"Done: {len(PROBES)} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
