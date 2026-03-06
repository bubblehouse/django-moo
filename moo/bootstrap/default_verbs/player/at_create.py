#!moo verb @create make --on $player --dspec any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to create an instance of an object or class. It parses the arguments to extract the
parent object we wish to create an instance of, along with the name we wish to give to the created object. The
`create()` primitive is called, with the derived parent added afterwards. The resulting object is moved to the player's
inventory, using the `move()` primitive.
"""

from moo.core import context, create, lookup

if not (context.parser.has_dobj_str()):
    print("[color yellow]What do you want to create?[/color yellow]")
    return

name = context.parser.get_dobj_str()
new_obj = create(name, location=None)
print("[color yellow]Created %s[/color yellow]" % new_obj)

if context.parser.has_pobj_str("from"):
    parent = context.parser.get_pobj("from", lookup=True)
    new_obj.parents.add(parent)
    print("[color yellow]Transmuted %s to %s[/color yellow]" % (new_obj, parent))

new_obj.moveto(context.player)
