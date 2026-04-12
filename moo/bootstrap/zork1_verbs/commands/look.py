#!moo verb look l --on $player --dspec either
# pylint: disable=return-outside-function,undefined-variable
"""Look at the current room or an object."""

from moo.sdk import context, NoSuchObjectError, NoSuchPropertyError

if context.parser.has_dobj_str():
    try:
        obj = context.parser.get_dobj()
    except NoSuchObjectError:
        print("You don't see that here.")
        return
    if obj.has_verb("look_action"):
        obj.invoke_verb("look_action")
    else:
        try:
            desc = obj.get_property("description")
            print(desc)
        except NoSuchPropertyError:
            print(f"There's nothing special about the {_.zork_sdk.desc(obj)}.")
else:
    room = context.player.location
    if room.has_verb("look_action"):
        room.invoke_verb("look_action")
    else:
        room.look_self()
