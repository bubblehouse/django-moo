#!moo verb wr*ite --on $book --dspec none --ispec in:any --ispec under:any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Write an entry to the book keyed by room ID. Entries accumulate rather than overwrite.
Any player may write from any location — the book is resolved via global lookup.

Usage:
    write in <book> under <topic> with "#9: text"   — stored as topic:#9
    write in <book> with "#9: text"               — stored as #9 (no topic)
"""

from moo.sdk import context, NoSuchObjectError

try:
    book = context.parser.get_pobj("in", lookup=True)
except NoSuchObjectError:
    print("No book found by that name.")
    return

text = context.parser.get_pobj_str("with").strip()
if not text.startswith("#"):
    print('Start your entry with a room ID, e.g.: write in book with "#9: Kitchen done."')
    return

colon = text.find(":")
if colon == -1:
    print('Include a colon after the room ID, e.g.: write in book with "#9: text"')
    return

room_id = text[:colon].strip()
body = text[colon + 1 :].strip()

topic = context.parser.get_pobj_str("under").strip().lower() if context.parser.has_pobj_str("under") else None
key = f"{topic}:{room_id}" if topic else room_id

notes = book.get_property("notes") or {}
existing = notes.get(key, "")
sep = "\n" if existing else ""
notes[key] = existing + sep + f"[{context.player.name}] {body}"
book.set_property("notes", notes)
print(f"Entry written for {room_id}{' [' + topic + ']' if topic else ''}.")
