#!moo verb @gag --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
The concept of gagging is fairly simple to understand. If there is a player or object you do not wish to see any output
from, then you can place the player or object into your gag list. If any output is sent to you from that object, using
its `tell` verb, then it is ignored, and not printed on your terminal screen.

Two gaglists are maintained: one for players (in the property `gaglist`) and one for objects (in the property
`object_gaglist`).

Three verbs are used to maintain and observe the list of objects that are in the gag lists. The `@gag` verb is used as
a player command to add objects to the gag lists.
"""

from moo.core import context, lookup

player = context.player

if player != this:
    player.tell("Permission denied.")
    return

victims = [lookup(arg) for arg in args]

if not victims:
    print("Usage:  @gag <player or object> [<player or object>...]")
    return

gagplayers = gagobjs = []
for i, victim in enumerate(victims):
    if victim.is_player():
        gagplayers.append(victim)
    else:
        gagobjs.append(victim)

changed = False
for p in gagplayers:
    if p in player.gaglist:
        print(f"You are already gagging {p.name}.")
    else:
        changed = True
        tmp = player.gaglist
        tmp.append(p)
        player.gaglist = tmp

for o in gagobjs:
    if o in player.object_gaglist:
        print(f"You are already gagging {o.name}.")
    else:
        changed = True
        tmp = player.object_gaglist
        tmp.append(o)
        player.object_gaglist = tmp

if changed:
    print("Gag list updated.")
else:
    print("No changes made to gag list.")
