#!moo verb n*orth e*ast s*outh w*est northwest northeast southwest southeast up down --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
In general, when a player wants to move out of a room using an exit, the recognition of the exit name is done by the
`huh` and `huh2` verbs for the room. However, to cope with the most common cases, verbs are defined for each of the
compass directions and up and down.

What this does is check to see if the exit is defined for the room. If it is, then the exit is `invoked`. If not, a
suitable message is sent to the player.

This case is included simply to speed up processing for certain common cases.
"""

from moo.core import context

player = context.player
exit = this.match_exit(verb_name)
if exit is None:
    player.tell("You can't go that way.")
elif isinstance(exit, list):
    player.tell(f"I don't know which '{verb_name}' you mean.")
else:
    exit.invoke(player)
