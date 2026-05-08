# vhs tape — animedex anilist backend tour (~22 s)
#
# Five short anilist demos covering: a typed Media show, a search,
# a character lookup, a studio lookup, and the trending rail.

Output anilist.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex anilist show 154587 --jq '{romaji: .title.romaji, year: .seasonYear, score: .averageScore}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex anilist search Frieren --jq '.[0:3] | map(.title.romaji)'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex anilist character 11 --jq '.name.full'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex anilist studio 11 --jq '.name'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex anilist trending --jq '.[0:5] | map(.title.romaji)'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
