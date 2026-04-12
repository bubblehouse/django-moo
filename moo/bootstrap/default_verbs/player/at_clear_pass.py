#!moo verb @clear_pass --on $player --dspec none --ispec for:any

# pylint: disable=return-outside-function,undefined-variable

"""
Clear the dispatch board room list and survey book notes for a specific chain.
Foreman calls this at the end of each full chain pass.

Usage: @clear_pass for <chain>

Only entries belonging to the named chain are removed. Other chains' data is
left intact — inspectors' accumulated notes are never cleared by tradesmen's Foreman.
"""

from moo.sdk import context, lookup, NoSuchObjectError

chain = context.parser.get_pobj_str("for").strip().lower()

if not chain:
    print("Usage: @clear_pass for <chain>")
    return

try:
    board = lookup("The Dispatch Board")
except NoSuchObjectError:
    print("Error: The Dispatch Board not found.")
    return

try:
    book = lookup("The Survey Book")
except NoSuchObjectError:
    print("Error: The Survey Book not found.")
    return

# Clear this chain's room list from the dispatch board
try:
    rooms_by_chain = board.get_property("rooms_by_chain") or {}
except Exception:
    rooms_by_chain = {}

rooms_by_chain = {k: v for k, v in rooms_by_chain.items() if k != chain}
board.set_property("rooms_by_chain", rooms_by_chain)

# Clear this chain's survey notes (prefix "chain:")
try:
    notes = book.get_property("notes") or {}
except Exception:
    notes = {}

prefix = f"{chain}:"
kept = {k: v for k, v in notes.items() if not k.startswith(prefix)}
book.set_property("notes", kept)

removed = len(notes) - len(kept)
print(f"Pass cleared for [{chain}]: room list removed, {removed} survey note(s) cleared.")
