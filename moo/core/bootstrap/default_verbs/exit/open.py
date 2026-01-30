#!moo verb open close unlock lock --on $exit --dspec any

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api

door_description = api.parser.get_dobj_str()
door = api.caller.location.match_exit(door_description)
if not door:
    print(f"There is no door called {door_description} here.")
    return

# this is the simplest kind of door, where access control is
# determined by the ownership of the corresponding properties
if verb_name == "open":
    if door.is_open():
        print("The door is already open.")
    else:
        if door.is_locked():
            print("The door is locked.")
        else:
            door.set_property("open", True)
            print("The door is open.")
elif verb_name == "close":
    if not door.is_open():
        print("The door is already closed.")
    else:
        door.set_property("open", False)
        if door.has_property("autolock") and door.get_property("autolock"):
            door.set_property("locked", True)
        print("The door is closed.")
elif verb_name == "unlock":
    if door.is_locked():
        door.set_property("locked", False)
        print("The door is unlocked.")
    else:
        print("The door is not locked.")
elif verb_name == "lock":
    if door.is_locked():
        print("The door is already locked.")
    else:
        door.set_property("locked", True)
        print("The door is locked.")
