#!moo verb lock unlock --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Lock or unlock an exit by direction name. Mirrors the exit/open.py lock/unlock logic
but dispatches via $room (like go.py) so it works for exits stored in the room's
exits property rather than in room contents.

Usage:
    lock south
    unlock south
"""

from moo.sdk import context

door_description = context.parser.get_dobj_str()
door = context.player.location.match_exit(door_description)
if not door:
    print(f"There is no exit called {door_description} here.")
    return

if verb_name == "lock":
    if door.is_locked():
        print("The door is already locked.")
    else:
        door.set_property("locked", True)
        print("The door is locked.")
elif verb_name == "unlock":
    if door.is_locked():
        door.set_property("locked", False)
        print("The door is unlocked.")
    else:
        print("The door is not locked.")
