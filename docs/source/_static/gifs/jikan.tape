# vhs tape — animedex jikan backend tour (~22 s)
#
# Five short jikan demos covering: anime full, manga full, character,
# season grid, and a top-anime listing.

Output jikan.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex jikan show 52991 --jq '.data | {title, score, status}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex jikan manga-show 2 --jq '.data | {title, score, chapters}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex jikan character-show 11 --jq '.data.name'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex jikan season 2024 spring --limit 5 --jq '.[].title'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex jikan top-anime --filter bypopularity --limit 3 --jq '.[].title'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
