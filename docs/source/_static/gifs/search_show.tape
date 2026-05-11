# vhs tape - animedex search/show aggregate tour (~18 s)
#
# Uses a pre-warmed local cache during rendering so the demo is stable
# and does not depend on live upstream rate-limit state.

Output search_show.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 1120
Set Height 540
Set Padding 14
Set Framerate 24

Hide
Type "export XDG_CACHE_HOME=$(mktemp -d) && python ../../../../tools/fixtures/prewarm_aggregate_cache.py && clear"
Enter
Sleep 1s
Show

Type "animedex search anime Frieren --limit 2 --source jikan,kitsu,shikimori"
Sleep 400ms
Enter
Sleep 3200ms

Type "animedex search manga Berserk --limit 2 --source mangadex,shikimori --jq '.items[] | {_prefix_id, _source}'"
Sleep 400ms
Enter
Sleep 3000ms

Type "animedex show anime mal:52991 --jq '{title, score, status}'"
Sleep 400ms
Enter
Sleep 2800ms

Type "animedex show character shikimori:184947 --jq '{id, name}'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
