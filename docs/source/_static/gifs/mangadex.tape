# vhs tape — animedex mangadex backend tour (~22 s)
#
# Four mangadex demos covering: search, show, feed (chapters), random.

Output mangadex.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex mangadex search 'Berserk' --limit 3 --jq '.[].attributes.title.en'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex mangadex show 801513ba-a712-498c-8f57-cae55b38cc92 --jq '.attributes | {title: .title.en, status, year}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex mangadex feed 801513ba-a712-498c-8f57-cae55b38cc92 --lang en --limit 3 --jq '.[].attributes | {chapter, title}'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex mangadex random-manga --jq '.attributes.title.en'"
Sleep 400ms
Enter
Sleep 2000ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
