# vhs tape — quickstart walkthrough (~25 s)
#
# A longer demo that builds the user's mental model:
#  1. animedex --help (the command tree),
#  2. real anilist show with TTY rendering,
#  3. a jq-projected JSON output,
#  4. multi-source comparison.

Output quickstart.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 560
Set Padding 14
Set Framerate 24

Type "animedex --help"
Sleep 400ms
Enter
Sleep 2200ms

Type "clear"
Enter
Sleep 200ms

Type "animedex anilist show 154587 --jq '{title: .title.romaji, year: .seasonYear, score: .averageScore}'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex nekos categories --json --jq '.[:8]'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex nekos image husbando --jq '.[0] | {url, artist: .artist_name}'"
Sleep 400ms
Enter
Sleep 2200ms

Sleep 600ms
