#!moo verb @post_rooms --on $player --dspec none --ispec for:any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Post a room ID list to the dispatch board for a specific agent chain.
Mason calls this before passing the token so subsequent trades know which rooms to visit.

Usage: @post_rooms for <chain> with "#9 | #22 | #37"

The list is stored under the chain name and overrides any prior list for that chain.
Other chains' lists are not affected.
"""

from moo.sdk import context, lookup, NoSuchObjectError

chain = context.parser.get_pobj_str("for").strip().lower()
rooms_str = context.parser.get_pobj_str("with").strip()

if not chain:
    print("Usage: @post_rooms for <chain> with <room-ids>")
    return

try:
    board = lookup("The Dispatch Board")
except NoSuchObjectError:
    print("Error: The Dispatch Board not found.")
    return

try:
    rooms_by_chain = board.get_property("rooms_by_chain") or {}
except Exception:
    rooms_by_chain = {}

rooms_by_chain[chain] = rooms_str
board.set_property("rooms_by_chain", rooms_by_chain)
print(f"Room list posted for [{chain}]: {rooms_str}")
