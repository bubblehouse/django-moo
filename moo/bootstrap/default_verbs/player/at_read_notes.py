#!moo verb @read_notes --on $player --dspec none --ispec for:any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Read survey book notes for a specific chain, optionally filtered to one room.

Usage: @read_notes for <chain>            — list all rooms with note previews
       @read_notes for <chain> from #9    — full notes for one room

Inspector and tradesman notes are stored separately — each chain only sees its own.
"""

from moo.sdk import context, lookup, NoSuchObjectError

chain = context.parser.get_pobj_str("for").strip().lower()

if not chain:
    print("Usage: @read_notes for <chain>")
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

prefix = f"{chain}:"

if context.parser.has_pobj_str("from"):
    room_id = context.parser.get_pobj_str("from").strip()
    key = f"{chain}:{room_id}"
    if key in notes:
        print(f"--- {room_id} [{chain}] ---")
        print(notes[key])
    else:
        print(f"No notes for {room_id} in [{chain}].")
else:
    matching = [(k, v) for k, v in notes.items() if k.startswith(prefix)]
    if not matching:
        print(f"No notes for chain [{chain}].")
        return
    for key, text in matching:
        room_id = key[len(prefix):]
        first_line = text.split("\n")[0]
        truncated = first_line[:65] + ("..." if len(first_line) > 65 else "")
        print(f"  {room_id}: {truncated}")
