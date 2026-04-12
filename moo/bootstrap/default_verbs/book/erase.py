#!moo verb er*ase --on $book --dspec this --ispec under:any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Erase entries from the book. Only the book's owner or a wizard may erase.

Usage:
    erase <book> under <topic>    — remove all entries under a topic
    erase <book> from #9        — remove the entry for a specific room
"""

from moo.sdk import context, lookup

wizard = lookup(1).wizard
if context.player != this.owner and not context.player.is_a(wizard):
    print("You don't have permission to erase pages from this book.")
    return

notes = this.get_property("notes") or {}

if context.parser.has_pobj_str("under"):
    topic = context.parser.get_pobj_str("under").strip().lower()
    prefix = f"{topic}:"
    before = len(notes)
    notes = {k: v for k, v in notes.items() if not k.startswith(prefix)}
    removed = before - len(notes)
    this.set_property("notes", notes)
    print(f"Erased {removed} entr{'y' if removed == 1 else 'ies'} for topic '{topic}'.")
elif context.parser.has_pobj_str("from"):
    room_id = context.parser.get_pobj_str("from").strip()
    if room_id in notes:
        notes.pop(room_id)
        this.set_property("notes", notes)
        print(f"Erased entry for {room_id}.")
    else:
        print(f"No entry for {room_id}.")
else:
    print("Usage: erase <book> under <topic>  or  erase <book> from #9")
