#!moo verb give --on $player --dspec any --ispec to:any
# pylint: disable=return-outside-function,undefined-variable
"""Give an object to a creature or character."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't have that.")
    return

if obj.location != context.player:
    print(f"You don't have the {_.zork_sdk.desc(obj)}.")
    return

if not context.parser.has_pobj_str("to"):
    print("Give it to whom?")
    return

try:
    target = context.parser.get_pobj("to")
except NoSuchObjectError:
    print("You don't see that here.")
    return

_.zork_sdk.move(obj, target)
print("Done.")
