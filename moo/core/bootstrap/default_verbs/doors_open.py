#!moo verb open close unlock lock --on "door class" --dspec any

from moo.core import api, write

if api.parser.has_dobj():
    door = api.parser.get_dobj()
else:
    door_description = api.parser.get_dobj_str()
    exits = api.caller.location.get_property("exits", {})
    for direction, exit in exits.items():  # pylint: disable=unused-variable,redefined-builtin
        if exit["door"].is_named(door_description):
            door = exit["door"]
            break
    else:
        print(f"There is no door called {door_description} here.")
        return  # pylint: disable=return-outside-function  # type: ignore

# this is the simplest kind of door, where access control is
# determined by the ownership of the corresponding properties
if api.parser.words[0] == "open":
    if door.is_open():
        print("The door is already open.")
    else:
        if door.is_locked():
            print("The door is locked.")
        else:
            door.set_property("open", True)
            print("The door is open.")
elif api.parser.words[0] == "close":
    if not door.is_open():
        print("The door is already closed.")
    else:
        door.set_property("open", False)
        if door.has_property("autolock") and door.get_property("autolock"):
            door.set_property("locked", True)
        print("The door is closed.")
elif api.parser.words[0] == "unlock":
    if door.is_locked():
        door.set_property("locked", False)
        print("The door is unlocked.")
    else:
        print("The door is not locked.")
elif api.parser.words[0] == "lock":
    if door.is_locked():
        print("The door is already locked.")
    else:
        door.set_property("locked", True)
        print("The door is locked.")
