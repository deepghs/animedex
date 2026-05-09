# GIF assets for animedex docs

This directory holds the rendered GIFs embedded by `README.md` and the
Sphinx docs landing page, alongside their [vhs](https://github.com/charmbracelet/vhs)
source tapes so future contributors can regenerate them.

## Files

| File | Use site | Source |
|---|---|---|
| `hero.gif` | top of `README.md`; first thing a visitor sees | `hero.tape` |
| `quickstart.gif` | `docs/source/quickstart.rst` walkthrough | `quickstart.tape` |
| `anilist.gif` | `docs/source/tutorials/backends/anilist.rst` header | `anilist.tape` |
| `ann.gif` | `docs/source/tutorials/backends/ann.rst` header | `ann.tape` |
| `jikan.gif` | `docs/source/tutorials/backends/jikan.rst` header | `jikan.tape` |
| `kitsu.gif` | `docs/source/tutorials/backends/kitsu.rst` header | `kitsu.tape` |
| `mangadex.gif` | `docs/source/tutorials/backends/mangadex.rst` header | `mangadex.tape` |
| `danbooru.gif` | `docs/source/tutorials/backends/danbooru.rst` header | `danbooru.tape` |
| `waifu.gif` | `docs/source/tutorials/backends/waifu.rst` header | `waifu.tape` |
| `trace.gif` | `docs/source/tutorials/backends/trace.rst` header | `trace.tape` |
| `nekos.gif` | `docs/source/tutorials/backends/nekos.rst` header | `nekos.tape` |
| `shikimori.gif` | `docs/source/tutorials/backends/shikimori.rst` header | `shikimori.tape` |

## Regenerating

The tapes assume `animedex` is on `$PATH`. Install the package in editable
mode first, then run vhs:

```bash
pip install -e .
which animedex                # confirm it resolves to the dev install

cd docs/source/_static/gifs
vhs hero.tape                 # produces hero.gif
vhs quickstart.tape           # produces quickstart.gif
vhs anilist.tape              # produces anilist.gif
vhs ann.tape                  # produces ann.gif
vhs jikan.tape                # produces jikan.gif
vhs kitsu.tape                # produces kitsu.gif
vhs mangadex.tape             # produces mangadex.gif
vhs danbooru.tape             # produces danbooru.gif
vhs waifu.tape                # produces waifu.gif
vhs trace.tape                # produces trace.gif
vhs nekos.tape                # produces nekos.gif
vhs shikimori.tape            # produces shikimori.gif
```

vhs is available as a single-file binary at
[github.com/charmbracelet/vhs/releases](https://github.com/charmbracelet/vhs/releases).
The render is local and offline-after-install — no network calls happen
inside vhs itself, but the recorded commands DO call out to the real
upstream backends (so they need network at record time). Each fresh
render captures whatever the upstream returned that moment; small drift
(a different random nekos image, a different anilist score) is expected
and does not invalidate the GIF.

## Why commit both .tape and .gif?

* The `.gif` is the artefact a docs reader sees — keep it readable.
* The `.tape` is the pinned recipe — keep regeneration trivial, prevent
  the rendered GIF from going stale silently.

CI does not regenerate GIFs (no vhs in the matrix), so they are
deliberately a manual maintenance step. Treat outdated GIFs as a docs
quality issue, not a build failure.
