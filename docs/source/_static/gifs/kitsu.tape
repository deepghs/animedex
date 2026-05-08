# vhs tape — animedex kitsu backend tour (~22 s)
#
# Four kitsu demos covering: anime show, search, mappings (cross-source
# ID graph), trending.

Output kitsu.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex kitsu show 7442 --jq '.attributes | {title: .canonicalTitle, status, averageRating}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex kitsu search 'Frieren' --limit 3 --jq '.[].attributes.canonicalTitle'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex kitsu mappings 7442 --jq '.[] | {site: .attributes.externalSite, id: .attributes.externalId}' | head -3"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex kitsu trending --limit 3 --jq '.[].attributes.canonicalTitle'"
Sleep 400ms
Enter
Sleep 2000ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
