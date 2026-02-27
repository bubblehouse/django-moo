#!moo verb @listgag listgag --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used as a player command to list the objects in the player's gag lists. If the gag lists are not empty, a
list of the names of the players in the `gaglist` property on the player, and the objects in the `object_gaglist`
property are produced.

The verb uses a test based on the `context.parser` object, to determine if it is being called by another verb, or
invoked by a player as a command. If `context.parser` returns `None` (and hence is not `True`), then the verb is being
invoked as a player command. When False, the verb is being invoked by another verb, and therefore returns JSON.

TODO: In addition, the verb checks through the gag lists of all the player's in the database, to see if the player who
TODO: invoked the command is listed in anyone else's gag list. If this is the case, a list of the people doing the
TODO: gagging is printed.
"""

from moo.core import context

player = context.player

if not context.parser:
    print("Gagged players:")
    if player.gaglist:
        for p in player.gaglist:
            print(f"  {p.name}")
    else:
        print("  None")

    print("Gagged objects:")
    if player.object_gaglist:
        for o in player.object_gaglist:
            print(f"  {o.name}")
    else:
        print("  None")
else:
    return {"gagged_players": player.gaglist, "gagged_objects": player.object_gaglist}
