#!moo verb go --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable,redefined-builtin

from moo.core import context

player = context.player
for dir in context.parser.words[1:]:
    if exit := player.location.match_exit(dir):
        exit.invoke(player)
    else:
        print("Go where?")
