"""Capture authenticated read-endpoint fixtures.

Wires the three auth schemes used by the four mid-tier backends:

* MangaDex Bearer (OAuth2 password grant against
  ``auth.mangadex.org``);
* Danbooru HTTP Basic (``username:api_key``);
* Waifu.im X-Api-Key.

Reads credentials from environment variables:

* ``ANIMEDEX_MANGADEX_CREDS`` =
  ``client_id:client_secret:username:password``
* ``ANIMEDEX_DANBOORU_CREDS`` = ``username:api_key``
* ``ANIMEDEX_WAIFU_TOKEN`` = ``<api-key>``

The capture pipeline redacts the ``Authorization`` and ``X-Api-Key``
headers via :func:`tools.fixtures.capture._redact_request_headers`
before writing the YAML to disk, so the on-disk fixture never holds
the raw token. Public IPs in the body are scrubbed to the RFC-5737
documentation address.
"""

from __future__ import annotations

import base64
import os
import sys

import requests

from tools.fixtures.capture import capture


PACE = 1.5
MD_BASE = "https://api.mangadex.org"
DB_BASE = "https://danbooru.donmai.us"
WI_BASE = "https://api.waifu.im"
MD_TOKEN_URL = "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token"


def _exchange_mangadex_password_grant() -> str:
    creds_raw = os.environ.get("ANIMEDEX_MANGADEX_CREDS", "")
    parts = creds_raw.split(":", 3)
    if len(parts) != 4:
        raise SystemExit(
            "ANIMEDEX_MANGADEX_CREDS must be 'client_id:client_secret:username:password'"
        )
    client_id, client_secret, username, password = parts
    r = requests.post(
        MD_TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        timeout=30.0,
    )
    r.raise_for_status()
    body = r.json()
    return body["access_token"]


def _basic_auth_header() -> str:
    creds = os.environ.get("ANIMEDEX_DANBOORU_CREDS", "")
    if ":" not in creds:
        raise SystemExit("ANIMEDEX_DANBOORU_CREDS must be 'username:api_key'")
    encoded = base64.b64encode(creds.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _waifu_apikey() -> str:
    key = os.environ.get("ANIMEDEX_WAIFU_TOKEN", "")
    if not key:
        raise SystemExit("ANIMEDEX_WAIFU_TOKEN must be set")
    return key


def main() -> int:
    total = 0

    # ---------- MangaDex (~14 fixtures) ----------
    print("-- MangaDex auth fixtures (running OAuth2 password grant)")
    bearer = _exchange_mangadex_password_grant()
    md_headers = {"Authorization": f"Bearer {bearer}"}
    md_probes = [
        ("user_me", "/user/me", None),
        ("user_follows_manga", "/user/follows/manga?limit=2", None),
        ("user_follows_group", "/user/follows/group?limit=2", None),
        ("user_follows_user", "/user/follows/user?limit=2", None),
        ("user_follows_list", "/user/follows/list?limit=2", None),
        ("user_follows_manga_feed", "/user/follows/manga/feed?limit=2", None),
        ("user_list", "/user/list?limit=2", None),
        ("user_history", "/user/history", None),
        ("manga_status", "/manga/status", None),
        # /manga/{id}/status + /read need a valid manga id; pick Berserk.
        ("manga_status_by_id", "/manga/801513ba-a712-498c-8f57-cae55b38cc92/status", None),
        ("manga_read_markers", "/manga/801513ba-a712-498c-8f57-cae55b38cc92/read", None),
        # /user/follows/manga/{id}: existence check; expect 404 (not following).
        (
            "user_follows_manga_by_id_not_followed",
            "/user/follows/manga/801513ba-a712-498c-8f57-cae55b38cc92",
            None,
        ),
        # /user/follows/group/{id}: ditto; expect 404.
        (
            "user_follows_group_by_id_not_followed",
            "/user/follows/group/0a8eb8f6-ed7b-4db6-90f8-fde18e1842e6",
            None,
        ),
    ]
    for label, suffix, _ in md_probes:
        capture(
            backend="mangadex",
            path_slug=label,
            label="default",
            method="GET",
            url=f"{MD_BASE}{suffix}",
            headers=md_headers,
            pace_seconds=PACE,
        )
        total += 1
        print(f"  mangadex {label}: ok")

    # ---------- Danbooru (~2 fixtures) ----------
    print("-- Danbooru auth fixtures")
    db_headers = {"Authorization": _basic_auth_header()}
    db_probes = [
        ("profile", "/profile.json"),
        ("saved_searches", "/saved_searches.json?limit=3"),
    ]
    for label, suffix in db_probes:
        capture(
            backend="danbooru",
            path_slug=label,
            label="default",
            method="GET",
            url=f"{DB_BASE}{suffix}",
            headers=db_headers,
            pace_seconds=PACE,
        )
        total += 1
        print(f"  danbooru {label}: ok")

    # ---------- Waifu.im (1 fixture) ----------
    print("-- Waifu.im auth fixtures")
    wi_headers = {"X-Api-Key": _waifu_apikey()}
    capture(
        backend="waifu",
        path_slug="users_me",
        label="default",
        method="GET",
        url=f"{WI_BASE}/users/me",
        headers=wi_headers,
        pace_seconds=PACE,
    )
    total += 1
    print("  waifu users_me: ok")

    print(f"Done: {total} authenticated fixtures captured (tokens redacted by the capture pipeline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
