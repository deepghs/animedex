"""
Capture Danbooru fixtures. 10 req/sec read; pace 0.15 sec.
"""

from __future__ import annotations

import sys

from tools.fixtures.capture import capture


BASE = "https://danbooru.donmai.us"
PACE = 0.15


PATHS = [
    (
        "posts_search",
        [
            ("touhou-rating-g-order-score", "/posts.json?tags=touhou+rating:g+order:score&limit=2"),
            ("touhou-rating-s", "/posts.json?tags=touhou+rating:s&limit=2"),
            ("touhou-rating-q", "/posts.json?tags=touhou+rating:q&limit=2"),
            ("touhou-rating-e", "/posts.json?tags=touhou+rating:e&limit=2"),
            ("touhou-marisa-only", "/posts.json?tags=touhou+marisa_kirisame&limit=2"),
            ("touhou-exclude-marisa", "/posts.json?tags=touhou+-marisa_kirisame&limit=2"),
            ("score-gt-100", "/posts.json?tags=touhou+score:%3E100&limit=2"),
            ("score-lt-10", "/posts.json?tags=touhou+score:%3C10&limit=2"),
            ("order-score-desc", "/posts.json?tags=touhou+order:score&limit=2"),
            ("order-date", "/posts.json?tags=touhou+order:date&limit=2"),
            ("order-random", "/posts.json?tags=touhou+order:random&limit=2"),
            ("multi-tag-cirno", "/posts.json?tags=touhou+cirno+1girl&limit=2"),
            ("with-rating-and-order", "/posts.json?tags=touhou+rating:g+order:score&limit=2"),
            ("blue-archive", "/posts.json?tags=blue_archive&limit=2"),
            ("genshin-impact", "/posts.json?tags=genshin_impact&limit=2"),
            ("page-cursor-before-id", "/posts.json?tags=touhou&limit=1&page=b8000000"),
        ],
    ),
    (
        "posts_by_id",
        [
            ("post-1", "/posts/1.json"),
            ("post-100", "/posts/100.json"),
            ("post-1000", "/posts/1000.json"),
            ("post-10000", "/posts/10000.json"),
            ("post-100000", "/posts/100000.json"),
            ("post-500000", "/posts/500000.json"),
            ("post-1000000", "/posts/1000000.json"),
            ("post-2000000", "/posts/2000000.json"),
            ("post-5000000", "/posts/5000000.json"),
            ("post-7000000", "/posts/7000000.json"),
            ("post-9000000", "/posts/9000000.json"),
            ("post-10000000", "/posts/10000000.json"),
            ("post-11000000", "/posts/11000000.json"),
            ("post-11200000", "/posts/11200000.json"),
            ("post-11300000", "/posts/11300000.json"),
            ("post-99999999-not-found", "/posts/99999999.json"),
        ],
    ),
    (
        "tags_search",
        [
            ("touhou-prefix", "/tags.json?search%5Bname_matches%5D=touhou*&limit=3"),
            ("naruto-prefix", "/tags.json?search%5Bname_matches%5D=naruto*&limit=3"),
            ("frieren-prefix", "/tags.json?search%5Bname_matches%5D=frieren*&limit=3"),
            ("hatsune-miku-substring", "/tags.json?search%5Bname_matches%5D=hatsune_miku&limit=3"),
            ("blue-prefix", "/tags.json?search%5Bname_matches%5D=blue_*&limit=3"),
            ("cirno-exact", "/tags.json?search%5Bname%5D=cirno&limit=3"),
            ("artist-category", "/tags.json?search%5Bname_matches%5D=zun&search%5Bcategory%5D=1&limit=3"),
            ("character-category", "/tags.json?search%5Bcategory%5D=4&limit=3"),
            ("copyright-category", "/tags.json?search%5Bcategory%5D=3&limit=3"),
            ("general-category", "/tags.json?search%5Bcategory%5D=0&limit=3"),
            ("meta-category", "/tags.json?search%5Bcategory%5D=5&limit=3"),
            ("by-post-count-min", "/tags.json?search%5Bpost_count%5D=%3E1000&limit=3"),
            ("order-count-desc", "/tags.json?search%5Border%5D=count&limit=3"),
            ("order-name-asc", "/tags.json?search%5Border%5D=name&limit=3"),
            ("touhou-deprecated", "/tags.json?search%5Bname_matches%5D=touhou*&search%5Bis_deprecated%5D=true&limit=3"),
            ("nonexistent-zzzzzz", "/tags.json?search%5Bname%5D=zzzzz_nope&limit=3"),
        ],
    ),
    (
        "artists_search",
        [
            ("zun", "/artists.json?search%5Bname%5D=zun&limit=2"),
            ("ke-ta", "/artists.json?search%5Bname%5D=ke-ta&limit=2"),
            ("matsuri-uta", "/artists.json?search%5Bname%5D=matsuri_uta&limit=2"),
            ("by-name-prefix-z", "/artists.json?search%5Bname%5D=z*&limit=2"),
            ("by-name-prefix-k", "/artists.json?search%5Bname%5D=k*&limit=2"),
            ("by-name-prefix-m", "/artists.json?search%5Bname%5D=m*&limit=2"),
            ("any-banned", "/artists.json?search%5Bis_banned%5D=true&limit=2"),
            ("any-active", "/artists.json?search%5Bis_banned%5D=false&limit=2"),
            ("order-name-asc", "/artists.json?search%5Border%5D=name&limit=2"),
            ("order-updated", "/artists.json?search%5Border%5D=updated_at&limit=2"),
            ("with-other-name", "/artists.json?search%5Bother_names_match%5D=zun&limit=2"),
            ("with-url-match", "/artists.json?search%5Burl_matches%5D=*pixiv*&limit=2"),
            ("created-after", "/artists.json?search%5Bcreated_at%5D=%3E2020-01-01&limit=2"),
            ("by-id", "/artists/1.json"),
            ("by-id-100", "/artists/100.json"),
            ("by-id-not-found", "/artists/99999999.json"),
        ],
    ),
    (
        "counts",
        [
            ("touhou-rating-g", "/counts/posts.json?tags=touhou+rating:g"),
            ("touhou-rating-s", "/counts/posts.json?tags=touhou+rating:s"),
            ("touhou-rating-q", "/counts/posts.json?tags=touhou+rating:q"),
            ("touhou-rating-e", "/counts/posts.json?tags=touhou+rating:e"),
            ("touhou-only", "/counts/posts.json?tags=touhou"),
            ("blue-archive", "/counts/posts.json?tags=blue_archive"),
            ("genshin-impact", "/counts/posts.json?tags=genshin_impact"),
            ("naruto", "/counts/posts.json?tags=naruto"),
            ("one-piece", "/counts/posts.json?tags=one_piece"),
            ("hatsune-miku", "/counts/posts.json?tags=hatsune_miku"),
            ("score-gt-1000", "/counts/posts.json?tags=score:%3E1000"),
            ("score-gt-500-touhou", "/counts/posts.json?tags=touhou+score:%3E500"),
            ("multi-cirno", "/counts/posts.json?tags=touhou+cirno"),
            ("multi-marisa", "/counts/posts.json?tags=touhou+marisa_kirisame"),
            ("frieren", "/counts/posts.json?tags=frieren"),
            ("nonexistent-tag", "/counts/posts.json?tags=zzz_nonexistent_tag_xyz"),
        ],
    ),
    (
        "pools_by_id",
        [
            ("pool-1", "/pools/1.json"),
            ("pool-100", "/pools/100.json"),
            ("pool-500", "/pools/500.json"),
            ("pool-1000", "/pools/1000.json"),
            ("pool-2000", "/pools/2000.json"),
            ("pool-5000", "/pools/5000.json"),
            ("pool-10000", "/pools/10000.json"),
            ("pool-15000", "/pools/15000.json"),
            ("pool-20000", "/pools/20000.json"),
            ("pool-25000", "/pools/25000.json"),
            ("pool-30000", "/pools/30000.json"),
            ("pool-not-found", "/pools/99999999.json"),
            ("pools-search-touhou", "/pools.json?search%5Bname_matches%5D=touhou*&limit=2"),
            ("pools-search-by-cat", "/pools.json?search%5Bcategory%5D=series&limit=2"),
            ("pools-order-updated", "/pools.json?search%5Border%5D=updated_at&limit=2"),
            ("pools-order-name", "/pools.json?search%5Border%5D=name&limit=2"),
        ],
    ),
]


def main() -> int:
    total = sum(len(group) for _, group in PATHS)
    print(f"Danbooru: {total} fixtures across {len(PATHS)} path families")
    for path_slug, group in PATHS:
        print(f"-- {path_slug} ({len(group)} fixtures)")
        for i, (label, suffix) in enumerate(group, 1):
            capture(
                backend="danbooru",
                path_slug=path_slug,
                label=label,
                method="GET",
                url=BASE + suffix,
                pace_seconds=PACE,
            )
            print(f"  [{i:02d}/{len(group)}] {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
