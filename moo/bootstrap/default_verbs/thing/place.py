#!moo verb place --on $thing --dspec this --ispec on:any --ispec under:any --ispec behind:any --ispec before:any --ispec beside:any --ispec over:any

# pylint: disable=return-outside-function,undefined-variable

"""
Place an object in a spatial relationship to another object in the current room. The object
being placed stays in the room; the placement is stored as metadata on the object.

Usage:
    place <object> on/under/behind/before/beside/over <target>

Examples:
    place book on desk
    place key under rug
    place coin behind painting

The ``surface_types`` property on the target restricts which prepositions are valid. If not
set, any placement preposition is accepted.

Objects placed with ``under`` or ``behind`` are hidden from the room contents list. They can
be found with ``look under <target>`` or ``look behind <target>``.
"""

from moo.sdk import context, NoSuchPropertyError, UsageError, PLACEMENT_PREPS

prep = None
for p in PLACEMENT_PREPS:
    if context.parser.has_pobj_str(p):
        prep = p
        break

if prep is None:
    raise UsageError(f"Usage: place <object> {'/'.join(PLACEMENT_PREPS)} <target>")

target = context.parser.get_pobj(prep)

if target == this:
    print("You can't place something on itself.")
    return

try:
    allowed = target.get_property("surface_types")
    if prep not in allowed:
        print(f"You can't place things {prep} the {target.title()}.")
        return
except NoSuchPropertyError:
    pass

this.set_placement(prep, target)

title = this.title()
tname = target.title()
print(f"You place {title} {prep} the {tname}.")
context.player.location.announce(f"{context.player.title()} places {title} {prep} the {tname}.")
