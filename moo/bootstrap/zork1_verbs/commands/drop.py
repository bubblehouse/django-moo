#!moo verb drop --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Drop an object from inventory into the current room."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't have that.")
    return

if obj.location != context.player:
    print(f"You don't have the {_.zork_sdk.desc(obj)}.")
    return

_.zork_sdk.move(obj, context.player.location)
print("Dropped.")
