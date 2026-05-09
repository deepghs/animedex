# vhs tape - animedex ghibli backend tour (~15 s)
#
# Offline snapshot demos: film filters, one character, species, and vehicles.

Output ghibli.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 1100
Set Height 500
Set Padding 14
Set Framerate 24

Type "animedex ghibli films --director 'Hayao Miyazaki' --min-rt-score 95 --jq 'map(.title)'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex ghibli people Haku --jq '.[0] | {name, age, eye_color, source: .source_tag.backend}'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex ghibli species --jq '[.[].name]'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex ghibli vehicles --jq '[.[].name]'"
Sleep 400ms
Enter
Sleep 2200ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
