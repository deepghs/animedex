# vhs tape — animedex danbooru backend tour (~22 s)
#
# Four danbooru demos covering: tag-DSL search (rating:g), one post,
# tag wildcard, count. All examples stay SFW per the project's posture
# of using rating:g when the user did not explicitly ask for adult
# content.

Output danbooru.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex danbooru search 'touhou marisa rating:g order:score' --limit 3 --jq '.[] | {id, score, rating}'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex danbooru post 1 --jq '{id, rating, score}'"
Sleep 400ms
Enter
Sleep 1800ms

Type "animedex danbooru tag 'touhou*' --limit 3 --jq '.[] | {name, post_count}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex danbooru count 'touhou rating:g' --jq '.counts.posts'"
Sleep 400ms
Enter
Sleep 1800ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
