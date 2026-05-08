# vhs tape — animedex nekos backend tour (~20 s)
#
# Five short nekos demos: list categories, fetch one image, fetch
# multi-amount, search, and project a single field.

Output nekos.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex nekos categories | head"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex nekos image husbando --jq '.[0].url'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex nekos image neko --amount 3 --jq '[.[].url]'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex nekos search Frieren --amount 3 --jq '[.[].artist_name] | unique'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex nekos image husbando --jq '.[0] | {url, artist: .artist_name, source: .source_url}'"
Sleep 400ms
Enter
Sleep 2400ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
