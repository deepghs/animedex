# vhs tape — animedex ann backend tour (~18 s)
#
# Four ANN demos covering: show, substring search, reports, and the
# 200-with-warning empty-result shape.

Output ann.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex ann show 38838 --jq '.anime[0] | {id, name, type}'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex ann search Frieren --jq '[.anime[] | {id, name}]'"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex ann reports --id 155 --type anime --nlist 2 --jq '.items[].fields.name'"
Sleep 400ms
Enter
Sleep 1900ms

Type "animedex ann show 99999999 --jq '{warnings, anime}'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
