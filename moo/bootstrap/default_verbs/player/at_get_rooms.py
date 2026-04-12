#!moo verb @get_rooms --on $player --dspec none --ispec for:any

# pylint: disable=return-outside-function,undefined-variable

"""
Read the room ID list from the dispatch board for a specific agent chain.
Workers call this on token receipt to get the rooms Mason built this pass.

Usage: @get_rooms for <chain>

Returns the pipe-separated room IDs posted by Mason, or "No rooms posted" if empty.
"""

from moo.sdk import context, lookup, NoSuchObjectError

chain = context.parser.get_pobj_str("for").strip().lower()

if not chain:
    print("Usage: @get_rooms for <chain>")
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

rooms_str = rooms_by_chain.get(chain, "")
if rooms_str:
    print(f"Rooms for [{chain}]: {rooms_str}")
else:
    print(f"No rooms posted for [{chain}].")
