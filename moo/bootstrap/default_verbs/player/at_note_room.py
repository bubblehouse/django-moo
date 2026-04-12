#!moo verb @note_room --on $player --dspec either --ispec for:any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Write a namespaced note to the survey book for a specific room and chain.
Workers call this after finishing each room. Notes accumulate and are
keyed by chain so two concurrent chains do not overwrite each other.

Usage: @note_room #9 for <chain> with "text"

Inspector notes persist across passes. Tradesman notes are cleared by
@clear_pass at the end of each chain loop.
"""

from moo.sdk import context, lookup, NoSuchObjectError

room_id = context.parser.get_dobj_str().strip()
chain = context.parser.get_pobj_str("for").strip().lower()
body = context.parser.get_pobj_str("with").strip()

if not room_id or not chain or not body:
    print("Usage: @note_room #N for <chain> with <text>")
    return

try:
    book = lookup("The Survey Book")
except NoSuchObjectError:
    print("Error: The Survey Book not found.")
    return

try:
    notes = book.get_property("notes") or {}
except Exception:
    notes = {}

key = f"{chain}:{room_id}"
existing = notes.get(key, "")
sep = "\n" if existing else ""
notes[key] = existing + sep + f"[{context.player.name}] {body}"
book.set_property("notes", notes)
print(f"Note written: [{chain}] {room_id}.")
