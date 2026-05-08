"""
One-shot migrator: convert existing JSON fixtures to YAML in place.

The first batch of the substrate API layer fixtures (anilist / jikan / kitsu / mangadex)
was captured before the YAML decision; rather than re-hit upstreams
this script reads each ``.json`` fixture, re-classifies the body
(parseable JSON -> ``body_json`` native dict; XML/HTML -> ``body_text``;
binary -> ``body_b64``), writes the same content as ``.yaml`` next to
it, then deletes the ``.json``.

Run once::

    python -m tools.fixtures.migrate_json_to_yaml

The script is idempotent: on a clean tree it finds nothing and exits 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = PROJECT_ROOT / "test" / "fixtures"


def _str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_representer)


def _classify(body_b64: Optional[str], body_text: Optional[str]) -> dict:
    out = {"body_json": None, "body_text": None, "body_b64": None}
    if body_text is not None:
        try:
            out["body_json"] = json.loads(body_text)
            return out
        except json.JSONDecodeError:
            out["body_text"] = body_text
            return out
    if body_b64:
        out["body_b64"] = body_b64
        return out
    out["body_text"] = ""
    return out


def migrate_one(json_path: Path) -> Optional[Path]:
    """Convert a single fixture; delete the source on success.

    :param json_path: Path to the ``.json`` fixture file.
    :type json_path: pathlib.Path
    :return: Path of the new ``.yaml`` file, or ``None`` if the
             corresponding YAML already exists.
    :rtype: pathlib.Path or None
    """
    yaml_path = json_path.with_suffix(".yaml")
    if yaml_path.exists():
        return None

    with open(json_path, "r", encoding="utf-8") as fh:
        old = json.load(fh)

    response = old["response"]
    body_b64 = response.get("body_b64")
    body_text = response.get("body_text")
    classification = _classify(body_b64, body_text)

    new = {
        "metadata": old["metadata"],
        "request": {
            "method": old["request"]["method"],
            "url": old["request"]["url"],
            "headers": old["request"]["headers"],
            "params": old["request"].get("params"),
            "json_body": old["request"].get("json_body"),
            "raw_body_b64": old["request"].get("raw_body_b64"),
        },
        "response": {
            "status": response["status"],
            "headers": response["headers"],
            **classification,
        },
    }

    with open(yaml_path, "w", encoding="utf-8") as fh:
        yaml.dump(new, fh, sort_keys=False, allow_unicode=True, default_flow_style=False, width=120)

    json_path.unlink()
    return yaml_path


def main() -> int:
    converted = 0
    skipped = 0
    json_files = sorted(FIXTURES_ROOT.rglob("*.json"))
    for jf in json_files:
        if "__pycache__" in jf.parts:
            continue
        result = migrate_one(jf)
        if result is None:
            skipped += 1
        else:
            converted += 1
    print(f"converted={converted}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
