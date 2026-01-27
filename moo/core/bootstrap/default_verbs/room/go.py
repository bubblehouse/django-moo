#!moo verb go --on $room --dspec any

from moo.core import api

player = api.player
for dir in api.parser.words[1:]:
    if exit := player.location.match_exit(dir):
        exit.invoke(player)
    else:
        player.tell("Go where?");
