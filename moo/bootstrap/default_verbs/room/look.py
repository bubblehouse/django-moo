#!moo verb look inspect --on $room --dspec either --ispec at:any --ispec through:any --ispec on:any --ispec under:any --ispec behind:any --ispec before:any --ispec beside:any --ispec over:any

# pylint: disable=return-outside-function,undefined-variable

"""
Look at various things in the player's current location. It can be used
meaningfully in other verbs, however, if the verb is called with no arguments. In this case, it calls the `look_self`
on the room which the verb was invoked on. You could use this verb to print the description of a room you are not in,
but it is stylistically better to use the `look_self()` verb of the room.

If a preposition is supplied, via this verb being invoked as a command, and there is no `on` or `in` preposition, then
the verb attempts to match the direct object with something in the room. If the match succeeds, the `look_self` verb of
the matched object is called to tell the player what the object looks like.

If an `on` or `in` preposition was used, then the player wishes to look inside a container of some sort, be it a member of
the `$container`` class, or in a player``s inventory, for example. An attempt is made to match the indirect object with
something in the room. If it succeeds, then an attempt is made to match the direct object with something inside the
container previously matched. If this final match is made, the `look_self` verb of the matched object is invoked to
print its description.

If the direct object is the empty string, `""``, then the container``s `look_self` verb is called to print its description.

Any ambiguous or failed matches produce suitable error messages.
"""

from moo.sdk import context, PLACEMENT_PREPS

PREP_DISPLAY = {"before": "in front of"}

# Handle spatial placement lookups: "look under rug", "look on desk", etc.
for prep in PLACEMENT_PREPS:
    if context.parser.has_pobj_str(prep):
        if not this.is_lit():
            print("It's too dark to see.")
            return
        target = context.parser.get_pobj(prep)
        found = [
            item
            for item in this.contents.all()
            if item.placement_prep == prep and item.placement_target_id == target.pk
        ]
        disp = PREP_DISPLAY.get(prep, prep)
        if found:
            names = _.string_utils.english_list(found)
            print(f"{disp.capitalize()} the {target.title()} you see {names}.")
        else:
            print(f"You find nothing {disp} the {target.title()}.")
        return

if context.parser.has_pobj_str("through"):
    direction = context.parser.get_pobj_str("through")
    exit_obj = context.player.location.match_exit(direction)
    if not exit_obj:
        print(f"[red]There is no exit called '{direction}' here.[/red]")
        return
    dest = exit_obj.get_property("dest")
    dest.look_self()
    return

if context.parser.has_pobj_str("in"):
    container = context.parser.get_pobj("in")
else:
    container = None

in_inventory = False
if context.parser.has_dobj() and container is None:
    obj = context.parser.get_dobj()
    in_inventory = obj.location_id == context.player.pk
elif context.parser.has_dobj_str():
    dobj_str = context.parser.get_dobj_str()
    if container:
        qs = container.find(dobj_str)
    else:
        inv_qs = context.player.find(dobj_str)
        if inv_qs:
            qs = inv_qs
            in_inventory = True
        else:
            qs = context.player.location.find(dobj_str)
    if not qs:
        print(f"There is no '{dobj_str}' here.")
        return
    obj = qs[0]
elif context.parser.has_pobj_str("at"):
    obj = context.parser.get_pobj("at", lookup=True)
    in_inventory = obj.location_id == context.player.pk
else:
    obj = context.player.location

if not in_inventory and obj != context.player.location and not this.is_lit():
    print("It's too dark to see.")
    return

obj.look_self()
