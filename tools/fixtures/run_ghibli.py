"""Capture Studio Ghibli API fixtures and refresh the offline snapshot.

The high-level Ghibli backend reads ``animedex/data/ghibli.json``
instead of hitting the network. Running with ``--snapshot`` refreshes
that committed bundle from the live API. Fixture capture writes one
list endpoint and one by-id endpoint per resource family.

Pacing: the Studio Ghibli API does not publish a formal cap. The
script defaults to one request per second, matching the transport's
conservative bucket for the live raw passthrough.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.fixtures.capture import capture


BASE = "https://ghibliapi.vercel.app"
RESOURCE_FAMILIES = ("films", "people", "locations", "species", "vehicles")


def _snapshot_path() -> Path:
    return Path(__file__).resolve().parents[2] / "animedex" / "data" / "ghibli.json"


def refresh_snapshot() -> dict:
    """Fetch and write the bundled Ghibli snapshot.

    :return: Snapshot dictionary.
    :rtype: dict
    """
    import requests

    snapshot = {}
    for family in RESOURCE_FAMILIES:
        response = requests.get(f"{BASE}/{family}", timeout=30)
        response.raise_for_status()
        snapshot[family] = response.json()
    _snapshot_path().write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot


def load_snapshot() -> dict:
    """Read the current committed snapshot."""
    return json.loads(_snapshot_path().read_text(encoding="utf-8"))


def main(argv=None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Capture Studio Ghibli API fixtures.")
    parser.add_argument("--snapshot", action="store_true", help="Refresh animedex/data/ghibli.json before capture.")
    parser.add_argument("--pace", type=float, default=1.0, help="Seconds to sleep before each request.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing fixture labels.")
    args = parser.parse_args(argv)

    snapshot = refresh_snapshot() if args.snapshot else load_snapshot()
    total = 0
    labels = {
        "films": "castle-in-the-sky",
        "people": "haku",
        "locations": "irontown",
        "species": "human",
        "vehicles": "goliath",
    }
    for family in RESOURCE_FAMILIES:
        print(f"-- /{family}")
        capture(
            backend="ghibli",
            path_slug=family,
            label=f"all-{family}",
            method="GET",
            url=f"{BASE}/{family}",
            pace_seconds=args.pace,
            overwrite=args.overwrite,
        )
        total += 1
        first_id = snapshot[family][0]["id"]
        capture(
            backend="ghibli",
            path_slug=f"{family}_by_id",
            label=labels[family],
            method="GET",
            url=f"{BASE}/{family}/{first_id}",
            pace_seconds=args.pace,
            overwrite=args.overwrite,
        )
        total += 1
    print(f"Done: {total} fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
