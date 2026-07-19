#!moo verb go --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable,redefined-builtin

from moo.sdk import context

player = context.player
moved = False
for dir in context.parser.words[1:]:
    # D (spec 200): stored exit first, then a computed/lattice exit.
    exit = player.location.match_exit(dir) or player.location.procedural_exit(dir)
    if exit:
        exit.invoke(player)
        moved = True
# Only complain once, and only if nothing in the command resolved to an exit —
# "go" with no direction, or a single unknown one.
if not moved:
    print("Go where?")
