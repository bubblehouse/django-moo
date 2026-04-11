#!moo verb er*ase --on $book --dspec this --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove the notes for a specific room from the book. Only the book's owner or a
wizard may erase pages.
Usage: erase <book> from "#9"    — remove notes for room #9
"""

from moo.sdk import context, lookup

wizard = lookup(1).wizard
if context.player != this.owner and not context.player.is_a(wizard):
    print("You don't have permission to erase pages from this book.")
    return

room_id = context.parser.get_pobj_str("from").strip()
notes = this.get_property("notes") or {}
if room_id in notes:
    notes.pop(room_id)
    this.set_property("notes", notes)
    print(f"Erased notes for {room_id}.")
else:
    print(f"No entry for {room_id}.")
