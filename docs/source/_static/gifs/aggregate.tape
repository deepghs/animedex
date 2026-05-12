# vhs tape - animedex calendar aggregate demo (~18 s)
#
# A compact tour of the new top-level aggregate commands:
#  1. season as a merged multi-source JSON envelope,
#  2. schedule as a timezone-aware TTY calendar block.

Output aggregate.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 1040
Set Height 560
Set Padding 14
Set Framerate 24

Type "python -m animedex season 2024 spring --limit 5 --json --no-cache --jq '{count: (.items | length), first: (.items[0] | {title: .title.romaji, sources: (.sources | map(.backend)), jikan_score: .source_details.jikan.score.score})}'"
Sleep 400ms
Enter
Sleep 3800ms

Type "clear"
Enter
Sleep 200ms

Type "python -m animedex schedule --day monday --source jikan --timezone +08:00 --limit 3 --no-cache"
Sleep 400ms
Enter
Sleep 3600ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
