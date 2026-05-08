# vhs tape — animedex trace backend tour (~16 s)
#
# Three trace demos: quota check (no cost), URL-based search with
# AniList inlining, and a `--jq` projection over the search hits.

Output trace.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 480
Set Padding 14
Set Framerate 24

Type "animedex trace quota --json --jq '{tier: .priority, used: .quota_used, total: .quota}'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info --jq '.[0] | {anime: .anilist_title.romaji, episode, similarity}'"
Sleep 500ms
Enter
Sleep 3000ms

Type "animedex trace search --url 'https://i.imgur.com/zLxHIeo.jpg' --anilist-info --jq '[.[].similarity]'"
Sleep 500ms
Enter
Sleep 3000ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
