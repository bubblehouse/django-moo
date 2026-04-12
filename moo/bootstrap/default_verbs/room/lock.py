#!moo verb lock unlock --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Lock or unlock an exit by direction name. Uses the same key-expression system as
containers and notes: the `key` property holds a keyexp evaluated by
`lock_utils.eval_key`. Storing the exit's own id as the keyexp always denies
traversal — no player can be or hold an exit.

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
        door.set_property("key", door.id)
        print("The door is locked.")
elif verb_name == "unlock":
    if door.is_locked():
        door.set_property("key", None)
        print("The door is unlocked.")
    else:
        print("The door is not locked.")
