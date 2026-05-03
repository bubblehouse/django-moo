#!moo verb lock unlock --on $room --dspec any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Lock or unlock an exit by direction name. Uses the same key-expression system as
containers and notes: the `key` property holds a keyexp evaluated by
`lock_utils.eval_key`.

Usage:
    lock south                 — sentinel lock (no one can pass)
    lock south with #123       — keyed lock (only holders of #123 can pass)
    lock south with "#12 || #34" — compound keyexp
    unlock south               — clear the lock

Without `with`, the exit's own id is stored as the keyexp, which always denies
traversal — no player can be or hold an exit.
"""

from moo.sdk import context

parser = context.parser
door_description = parser.get_dobj_str()
door = context.player.location.match_exit(door_description)
if not door:
    print(f"There is no exit called {door_description} here.")
    return

if verb_name == "lock":
    if door.is_locked():
        print("The door is already locked.")
        return
    if parser.has_pobj_str("with"):
        expr = parser.get_pobj_str("with").strip("'").strip('"')
        try:
            keyexp = _.lock_utils.parse_keyexp(expr)
        except ValueError:
            print("That doesn't look like a valid key expression.")
            return
        door.set_property("key", keyexp)
    else:
        door.set_property("key", door.id)
    print("The door is locked.")
elif verb_name == "unlock":
    if door.is_locked():
        door.set_property("key", None)
        print("The door is unlocked.")
    else:
        print("The door is not locked.")
