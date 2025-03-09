#!moo verb open close unlock lock --on "door class"

from moo.core import api, write

door = api.parser.get_dobj()

# this is the simplest kind of door, where access control is
# determined by the ownership of the corresponding properties
if api.parser.verb.name == "open":
    if door.is_open:
        write(api.caller, "The door is already open.")
    else:
        if door.is_locked:
            write(api.caller, "The door is locked.")
        else:
            door.set_property("open", True)
elif api.parser.verb.name == "close":
    if not door.is_open():
        write(api.caller, "The door is already closed.")
    else:
        door.set_property("open", False)
        if door.has_property("autolock") and door.get_property("autolock"):
            door.set_property("locked", True)
elif api.parser.verb.name == "unlock":
    if door.is_locked:
        door.set_property("locked", False)
    else:
        write(api.caller, "The door is not locked.")
elif api.parser.verb.name == "lock":
    if door.is_locked:
        write(api.caller, "The door is already locked.")
    else:
        door.set_property("locked", True)
