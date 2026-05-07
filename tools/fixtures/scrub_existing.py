"""One-shot: post-process committed fixtures to apply the M1 scrub.

Read every YAML under ``test/fixtures/``, run the response-headers
dict through :func:`tools.fixtures.capture.scrub_capture_response_headers`,
and rewrite the file in place when something changed. Idempotent.

Run from the repo root::

    python tools/fixtures/scrub_existing.py

This script is one-shot. After the bulk scrub lands, future captures
go through ``capture.py`` directly, which now scrubs at write time.
The script is kept around so a contributor running an older capture
script can rerun it before opening their PR.
"""

from __future__ import annotations

import yaml

from tools.fixtures.capture import (
    FIXTURES_ROOT,
    _str_representer,
    replace_public_ips_with_placeholder,
    scrub_capture_response_headers,
)


def main() -> int:
    yaml.add_representer(str, _str_representer)

    changed = 0
    scanned = 0
    for path in FIXTURES_ROOT.rglob("*.yaml"):
        scanned += 1
        text = path.read_text(encoding="utf-8")

        # Pass 1 — generic public-IPv4 replacement. Cheaper to do as
        # raw-string rewrite than to round-trip through YAML and walk
        # the tree, and any IP anywhere in the file (header value,
        # body text, embedded JSON string) gets the same treatment.
        scrubbed_text = replace_public_ips_with_placeholder(text)
        if scrubbed_text != text:
            text = scrubbed_text
            changed_in_this_file = True
        else:
            changed_in_this_file = False

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            if changed_in_this_file:
                path.write_text(text, encoding="utf-8")
                changed += 1
            continue

        # Pass 2 — header scrub. Round-trips through YAML so the
        # output stays canonical.
        response = data.get("response") or {}
        headers = response.get("headers") or {}
        scrubbed_headers = scrub_capture_response_headers(headers)
        headers_changed = scrubbed_headers != headers
        if headers_changed:
            response["headers"] = scrubbed_headers

        if headers_changed or changed_in_this_file:
            with open(path, "w", encoding="utf-8") as fh:
                yaml.dump(
                    data,
                    fh,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                    width=120,
                )
            changed += 1
    print(f"scrubbed {changed} of {scanned} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
