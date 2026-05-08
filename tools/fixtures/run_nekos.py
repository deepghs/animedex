"""
Capture nekos.best v2 fixtures.

Captures the three JSON-emitting endpoints in numbers sufficient for
both the lossless round-trip test (per-record parametrisation) and
the CLI tests (single-shot validation of each high-level command).

* ``/endpoints`` — captured 1x (response is deterministic enough
  that one snapshot pins the shape; future drift is caught by the
  per-row ``NekosCategoryFormat`` lossless check).
* ``/<category>?amount=N`` — captured for ``husbando`` / ``neko`` /
  ``waifu`` / ``katana`` (a GIF-format category, type=2 surface). One
  call per category at ``amount=1`` and one at ``amount=3`` so the
  fixture corpus exercises both the singleton and multi-result
  shapes.
* ``/search?...`` — captured for two query phrases (one that
  matches, one that returns an empty result) so test code can pin
  both branches.

Pacing: nekos.best does not publish a formal cap; the transport
applies a ~10 req/sec soft ceiling. ``PACE = 0.5`` keeps the capture
script visibly polite (one call every 500 ms, no concurrency) which
is roughly 2 req/sec — well under any practical threshold.
"""

from __future__ import annotations

import sys
from urllib.parse import urlencode

from tools.fixtures.capture import capture


BASE = "https://nekos.best/api/v2"
PACE = 0.5


CATEGORIES_TO_PROBE = (
    ("husbando", "image", 1),
    ("husbando", "image", 3),
    ("neko", "image", 1),
    ("waifu", "image", 1),
    ("baka", "gif", 1),  # GIF-format category — exercises the type=2 surface
)


SEARCH_PROBES = (
    ("frieren-image", {"query": "Frieren", "type": 1, "amount": 5}),
    ("frieren-gif", {"query": "Frieren", "type": 2, "amount": 3}),
    ("nonsense-no-match", {"query": "zzzzzzzzzzzzzzz-no-such-anime", "type": 1, "amount": 5}),
)


def main() -> int:
    total = 0

    print("-- /endpoints (1 fixture)")
    capture(
        backend="nekos",
        path_slug="endpoints",
        label="all-categories",
        method="GET",
        url=f"{BASE}/endpoints",
        pace_seconds=PACE,
    )
    total += 1
    print(f"  [01/01] /endpoints snapshot")

    print(f"-- /<category> ({len(CATEGORIES_TO_PROBE)} fixtures)")
    for i, (cat, fmt, amount) in enumerate(CATEGORIES_TO_PROBE, 1):
        url = f"{BASE}/{cat}?amount={amount}"
        capture(
            backend="nekos",
            path_slug=cat,
            label=f"{fmt}-amount-{amount}",
            method="GET",
            url=url,
            pace_seconds=PACE,
        )
        total += 1
        print(f"  [{i:02d}/{len(CATEGORIES_TO_PROBE)}] /{cat} amount={amount}")

    print(f"-- /search ({len(SEARCH_PROBES)} fixtures)")
    for i, (label, params) in enumerate(SEARCH_PROBES, 1):
        url = f"{BASE}/search?{urlencode(params)}"
        capture(
            backend="nekos",
            path_slug="search",
            label=label,
            method="GET",
            url=url,
            pace_seconds=PACE,
        )
        total += 1
        print(f"  [{i:02d}/{len(SEARCH_PROBES)}] /search {label}")

    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
