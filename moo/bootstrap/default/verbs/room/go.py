#!moo verb go --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable,redefined-builtin

from moo.sdk import context

player = context.player
for dir in context.parser.words[1:]:
    # D (spec 200): stored exit first, then a computed/lattice exit.
    exit = player.location.match_exit(dir) or player.location.procedural_exit(dir)
    if exit:
        exit.invoke(player)
    else:
        print("Go where?")
