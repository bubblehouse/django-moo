#!moo verb put place insert --on $player --dspec any --ispec in:any on:any
# pylint: disable=return-outside-function,undefined-variable
"""Put an object into or onto a container."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't have that.")
    return

container = None
for prep in ("in", "on", "into", "onto"):
    if context.parser.has_pobj_str(prep):
        try:
            container = context.parser.get_pobj(prep)
            break
        except NoSuchObjectError:
            print("You don't see that here.")
            return

if container is None:
    print("Put it where?")
    return

if obj.location != context.player:
    print(f"You don't have the {_.zork_sdk.desc(obj)}.")
    return

_.zork_sdk.move(obj, container)
print("Done.")
