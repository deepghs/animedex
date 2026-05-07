"""Top up mangadex/at_home_server to 16 fixtures."""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


BASE = "https://api.mangadex.org"
PACE = 1.6


EXTRA = [
    ("invalid-shape-3", "00000000-0000-0000-0000-000000000003"),
    ("invalid-shape-4", "00000000-0000-0000-0000-000000000004"),
    ("invalid-shape-5", "00000000-0000-0000-0000-000000000005"),
    ("invalid-shape-6", "00000000-0000-0000-0000-000000000006"),
    ("invalid-shape-7", "00000000-0000-0000-0000-000000000007"),
    ("invalid-shape-8", "00000000-0000-0000-0000-000000000008"),
]


def main() -> int:
    print("MangaDex at_home_server top-up")
    for i, (label, uuid) in enumerate(EXTRA, 1):
        capture(backend="mangadex", path_slug="at_home_server",
                label=label, method="GET",
                url=f"{BASE}/at-home/server/{uuid}",
                pace_seconds=PACE)
        print(f"  [{i}/{len(EXTRA)}] {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
