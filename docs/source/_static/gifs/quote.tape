# vhs tape - animedex quote backend tour (~14 s)
#
# Uses a pre-warmed local cache during rendering so the demo is stable
# and does not consume AnimeChan's anonymous hourly quota.

Output quote.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 1100
Set Height 500
Set Padding 14
Set Framerate 24

Hide
Type "export XDG_CACHE_HOME=$(mktemp -d) && python ../../../../tools/fixtures/prewarm_quote_cache.py && clear"
Enter
Sleep 1s
Show

Type "animedex quote random --jq '{quote: .content, anime: .anime.name, character: .character.name}'"
Sleep 400ms
Enter
Sleep 1800ms

Type "animedex quote quotes-by-character Saitama --jq '.[0] | {quote: .content, anime: .anime.name, character: .character.name}'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex quote anime 188 --jq '{id, name, episodeCount}'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
