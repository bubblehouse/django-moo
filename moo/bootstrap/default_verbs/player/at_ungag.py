#!moo verb @ungag --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used as a player command to remove an object from one of the player's gag lists, if it is a member. The
dobjstr is used as the name of the thing to remove from the gag list.

If this name is `everyone' then the player gag and object gag lists are reset to the empty list. Otherwise, if a valid
direct object has been referred to, by checking `parser.get_dobj()`, that is used as the object to gag. Otherwise, an
attempt is made to match the dobjstr with something in the player gag list. If no match is found, it is retried with
the object gag list. If this fails, the command is aborted with an error message.

If a valid match is found, it is removed from the relevant list, and the player informed.
"""

from moo.core import context

player = context.player
target = context.parser.get_dobj_str()

if target == "everyone":
    player.gaglist = []
    player.object_gaglist = []
    print("Gag lists cleared.")
    return

target = context.parser.get_dobj()
if target in player.gaglist:
    gaglist = player.gaglist
    gaglist.remove(target)
    player.gaglist = gaglist
    print(f"You are no longer gagging {target.name}.")
elif target in player.object_gaglist:
    gaglist = player.object_gaglist
    gaglist.remove(target)
    player.object_gaglist = gaglist
    print(f"You are no longer gagging {target.name}.")
else:
    print(f"You are not gagging {target.name}.")
