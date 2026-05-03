#!moo verb open close --on $exit --dspec any

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

from moo.sdk import context, NoSuchPropertyError

door_description = context.parser.get_dobj_str()
door = context.caller.location.match_exit(door_description)
if not door:
    print(f"There is no door called {door_description} here.")
    return

if verb_name == "open":
    if door.is_open():
        print("The door is already open.")
    else:
        if not door.is_unlocked_for(context.caller):
            print("The door is locked.")
        else:
            door.set_property("open", True)
            print("The door is open.")
elif verb_name == "close":
    if not door.is_open():
        print("The door is already closed.")
    else:
        door.set_property("open", False)
        try:
            autolock = door.get_property("autolock")
        except NoSuchPropertyError:
            autolock = False
        if autolock:
            door.set_property("key", door.id)
        print("The door is closed.")
