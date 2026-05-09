# vhs tape - animedex shikimori backend tour (~24 s)
#
# Uses a pre-warmed local cache during rendering so the demo is stable
# and does not depend on live Shikimori rate-limit state.

Output shikimori.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Hide
Type "export XDG_CACHE_HOME=$(mktemp -d) && python ../../../../tools/fixtures/prewarm_shikimori_cache.py && clear"
Enter
Sleep 1s
Show

Type "animedex shikimori show 52991 --jq '{id, name, status, episodes}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex shikimori manga-show 2 --jq '{id, name, kind, status}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex shikimori ranobe-show 23751 --jq '{id, name, kind, volumes, chapters}'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex shikimori publishers --jq '[.[0] | {id, name}]'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex shikimori person 1870 --jq '{id, name, website}'"
Sleep 400ms
Enter
Sleep 2400ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
