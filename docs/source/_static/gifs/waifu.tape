# vhs tape — animedex waifu backend tour (~22 s)
#
# Four waifu demos covering: tags catalogue, SFW image search,
# included-tag filter, public stats. Stays SFW (no --is-nsfw) per
# the upstream's default posture.

Output waifu.gif

Set Theme "Dracula"
Set FontSize 13
Set Width 920
Set Height 520
Set Padding 14
Set Framerate 24

Type "animedex waifu tags --jq '.[] | {slug, imageCount}' | head -8"
Sleep 400ms
Enter
Sleep 2200ms

Type "animedex waifu images --included-tags waifu --page-size 3 --jq '.[] | {id, isNsfw}'"
Sleep 400ms
Enter
Sleep 2000ms

Type "animedex waifu tag-by-slug waifu --jq '.description'"
Sleep 400ms
Enter
Sleep 1700ms

Type "animedex waifu stats-public --jq '{totalImages, totalTags, totalArtists}'"
Sleep 400ms
Enter
Sleep 2000ms

# Hold the final frame so a viewer has time to read the last block.
Sleep 4s
