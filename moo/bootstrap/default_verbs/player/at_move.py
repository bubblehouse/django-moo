#!moo verb @move --on $player --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to move objects from one location to another. The direct and indirect object strings are
used to match an object and location to move to. The `moveto` verb on the direct object is invoked to move it to the
indirect object location. If the location changes, and the object is a player, then the message

    blip disappears suddenly for parts unknown.

is displayed in the player's location before the move took place. Similarly, at the new location, the message

    blip materializes out of thin air.

is printed to the objects in the destination room. No messages are printed if an object is moved. If a permission
problem is found, it is reported to the player who typed the command.
"""

from moo.sdk import context, lookup

parser = context.parser
obj = parser.get_dobj()
destination = parser.get_pobj("to", lookup=True)
if obj.is_player():
    obj.announce(_.string_utils.pronoun_sub("%D disappears suddenly for parts %i(to)."))
result = obj.moveto(destination)
if result is False:
    dobj_str = parser.get_dobj_str()
    matches = lookup(dobj_str, return_first=False)
    if not matches:
        print(f"[red]{obj} cannot be moved.[/red]")
    elif len(matches) == 1:
        loc = matches[0].location
        where = str(loc) if loc else "the void"
        print(f"[red]{obj} cannot be moved (currently in {where}).[/red]")
    else:
        print(f"[red]{obj} cannot be moved. Objects named '{dobj_str}':[/red]")
        for m in matches:
            loc = m.location
            where = str(loc) if loc else "the void"
            print(f"  {m} — {where}")
    return
if obj.is_player():
    destination.announce(_.string_utils.pronoun_sub("%D materializes out of thin air in %i(to)."))
print(f"Moved {obj} to {destination}.")
