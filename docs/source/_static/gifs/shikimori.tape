# vhs tape — animedex shikimori backend tour (~20 s)
#
# Four Shikimori demos covering: anime show, title search, calendar,
# and media rails.

Output shikimori.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex shikimori show 52991 --jq '{id, name, status, episodes}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex shikimori search Frieren --limit 2 --jq '[.[].name]'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex shikimori calendar --limit 3 --jq '.[0:3] | map({episode: .next_episode, title: .anime.name})'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex shikimori videos 52991 --jq '[.[0:3][] | {name, kind, url}]'"
Sleep 400ms
Enter
Sleep 2400ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
