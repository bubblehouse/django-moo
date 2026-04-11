#!moo verb wr*ite --on $book --dspec none --ispec in:this --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Add a note to the book keyed by room ID. The entry must start with a room ID
(e.g. "#9:"), followed by the note text. Multiple writes for the same room
accumulate rather than overwrite. Any player may write.
Usage: write in <book> with "#9: text"
"""

from moo.sdk import context

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

notes = this.get_property("notes") or {}
existing = notes.get(room_id, "")
sep = "\n" if existing else ""
notes[room_id] = existing + sep + f"[{context.player.name}] {body}"
this.set_property("notes", notes)
print(f"Entry written for {room_id}.")
