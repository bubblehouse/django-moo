#!moo verb look inspect --on $room --dspec either --ispec at:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to look at various things in the player's current location. It can be used
meaningfully in other verbs, however, if the verb is called with no arguments. In this case, it calls the `look_self`
on the room which the verb was invoked on. You could use this verb to print the description of a room you are not in,
but it is stylistically better to use the `look_self()` verb of the room.

If a preposition is supplied, via this verb being invoked as a command, and there is no `on` or `in` preposition, then
the verb attempts to match the direct object with something in the room. If the match succeeds, the `look_self` verb of
the matched object is called to tell the player what the object looks like.

If an `on` or `in` preposition was used, then the player wishes to look inside a container of some sort, be it a member of
the `$container` class, or in a player's inventory, for example. An attempt is made to match the indirect object with
something in the room. If it succeeds, then an attempt is made to match the direct object with something inside the
container previously matched. If this final match is made, the `look_self` verb of the matched object is invoked to
print its description.

If the direct object is the empty string, `""`, then the container's `look_self` verb is called to print its description.

Any ambiguous or failed matches produce suitable error messages.
"""

from moo.core import context

if context.parser.has_pobj_str("in"):
    container = context.parser.get_pobj("in")
else:
    container = None

if context.parser.has_dobj() and container is None:
    obj = context.parser.get_dobj()
elif context.parser.has_dobj_str():
    dobj_str = context.parser.get_dobj_str()
    if container:
        qs = container.find(dobj_str)
    else:
        qs = context.player.find(dobj_str) or context.player.location.find(dobj_str)
    if not qs:
        print(f"There is no '{dobj_str}' here.")
        return
    obj = qs[0]
elif context.parser.has_pobj_str("at"):
    pobj_str = context.parser.get_pobj_str("at")
    if container:
        qs = container.find(pobj_str)
    else:
        qs = context.player.find(pobj_str) or context.player.location.find(pobj_str)
    if not qs:
        print(f"There is no '{pobj_str}' here.")
        return
    obj = qs[0]
else:
    obj = context.player.location

obj.look_self()
