#!moo verb @create make --on $player --dspec any --ispec from:any --ispec in:any

# pylint: disable=return-outside-function,undefined-variable

"""
Create an instance of an object or class. It parses the arguments to extract the
parent object we wish to create an instance of, along with the name we wish to give to the created object. The
`create()`` primitive is called, with the derived parent added afterwards. The resulting object is moved to the player``s
inventory, using the `move()` primitive.

Special syntax: @create "name" from "parent" in the void
  Creates object with location = None (not in player's inventory or any room)
"""

from moo.sdk import context, create, set_task_perms

if not (context.parser.has_dobj_str()):
    print("[yellow]What do you want to create?[/yellow]")
    return

name = context.parser.get_dobj_str()

# Resolve location before calling create() so it can be placed via ORM,
# bypassing any moveto verb (e.g. $furniture.moveto returns False for non-wizards).
location = None
place_in_void = False
if context.parser.has_pobj_str("in"):
    location_str = context.parser.get_pobj_str("in").lower()
    if location_str == "void":
        place_in_void = True
    else:
        location = context.parser.get_pobj("in", lookup=True)

if not place_in_void and location is None:
    # No "in" specified — pass player's inventory as location directly to create(),
    # so the accept/PermissionError check and the initial INSERT happen in a single
    # atomic save. This prevents orphan objects if the location rejects the new item.
    location = context.player

with set_task_perms(context.player):
    new_obj = create(name, owner=context.player, location=location)
    print("[yellow]Created %s[/yellow]" % new_obj)

    if context.parser.has_pobj_str("from"):
        parent = context.parser.get_pobj("from", lookup=True)
        new_obj.add_parent(parent)
        print("[yellow]Transmuted %s to %s[/yellow]" % (new_obj, parent))

if place_in_void:
    print("[yellow]%s exists in the void[/yellow]" % new_obj)
