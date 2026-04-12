#!moo verb take get pick --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Take an object from the current room or a container."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't see that here.")
    return

if obj.location == context.player:
    print(f"You already have the {_.zork_sdk.desc(obj)}.")
    return

if not _.zork_sdk.flag(obj, "takeable"):
    print(f"You can't take the {_.zork_sdk.desc(obj)}.")
    return

_.zork_sdk.move(obj, context.player)
print("Taken.")

if obj.has_verb("take_action"):
    obj.invoke_verb("take_action")
