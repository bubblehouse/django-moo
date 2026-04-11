#!moo verb r*ead --on $book --dspec this --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Read the book. With no argument, list all room IDs with a preview of each entry.
With a room ID via "from", show the full notes for that room.
Usage: read <book>               — index
       read <book> from "#9"     — single page
"""

from moo.sdk import context

notes = this.get_property("notes") or {}

if context.parser.has_pobj_str("from"):
    room_id = context.parser.get_pobj_str("from").strip()
    if room_id not in notes:
        print(f"No entry for {room_id}.")
        return
    print(f"--- {room_id} ---")
    print(notes[room_id])
else:
    if not notes:
        print("The book is empty.")
        return
    for room_id, text in notes.items():
        first_line = text.split("\n")[0]
        truncated = first_line[:70] + ("..." if len(first_line) > 70 else "")
        print(f"  {room_id}: {truncated}")
