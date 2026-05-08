# vhs tape — animedex hero demo (~10 s)
#
# Showcases the four-source aggregation pitch in roughly the time it
# takes to read a tweet: query AniList, query Jikan (MyAnimeList),
# fetch a nekos image — every result carries [src: <backend>].

Output hero.gif

Set Theme "Dracula"
Set FontSize 14
Set Width 880
Set Height 460
Set Padding 14
Set Framerate 24

Type "animedex anilist show 154587 --jq '.title.romaji'"
Sleep 600ms
Enter
Sleep 1500ms

Type "animedex jikan show 52991 --jq '.data.title'"
Sleep 600ms
Enter
Sleep 1500ms

Type "animedex nekos categories --json --jq '.[:5]'"
Sleep 600ms
Enter
Sleep 1800ms

Sleep 600ms
