#!moo verb throw toss --on $player --dspec any --ispec at:any
# pylint: disable=return-outside-function,undefined-variable
"""Throw an object, optionally at a target."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't have that.")
    return

if obj.location != context.player:
    print(f"You don't have the {_.zork_sdk.desc(obj)}.")
    return

if context.parser.has_pobj_str("at"):
    try:
        target = context.parser.get_pobj("at")
    except NoSuchObjectError:
        print("You don't see that here.")
        return
    if obj.has_verb("throw_at_action"):
        obj.invoke_verb("throw_at_action", target)
    else:
        _.zork_sdk.move(obj, context.player.location)
        print(f"You throw the {_.zork_sdk.desc(obj)} at the {_.zork_sdk.desc(target)}, but nothing happens.")
else:
    if obj.has_verb("throw_action"):
        obj.invoke_verb("throw_action")
    else:
        _.zork_sdk.move(obj, context.player.location)
        print(f"You throw the {_.zork_sdk.desc(obj)}. It lands nearby.")
