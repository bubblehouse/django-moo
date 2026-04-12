#!moo verb r*ead --on $book --dspec this --ispec under:any --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Read the survey book.

Usage:
    read <book>                         — index of all entries
    read <book> under <topic>             — index of entries under a topic
    read <book> under <topic> from #9     — full entry for room #9 under topic
    read <book> from #9                 — full entry for room #9 (no topic)
"""

from moo.sdk import context

notes = this.get_property("notes") or {}
has_topic = context.parser.has_pobj_str("under")
has_room = context.parser.has_pobj_str("from")

topic = context.parser.get_pobj_str("under").strip().lower() if has_topic else None
room_id = context.parser.get_pobj_str("from").strip() if has_room else None

if has_room:
    key = f"{topic}:{room_id}" if topic else room_id
    if key not in notes:
        print(f"No entry for {room_id}{' [' + topic + ']' if topic else ''}.")
        return
    print(f"--- {room_id}{' [' + topic + ']' if topic else ''} ---")
    print(notes[key])
    return

prefix = f"{topic}:" if topic else None
matching = [(k, v) for k, v in notes.items() if (prefix is None or k.startswith(prefix))]

if not matching:
    print(f"No entries for topic '{topic}'." if topic else "The book is empty.")
    return

for key, text in matching:
    display_id = key[len(prefix):] if prefix else key
    first_line = text.split("\n")[0]
    truncated = first_line[:70] + ("..." if len(first_line) > 70 else "")
    label = f"{display_id} [{topic}]" if topic else key
    print(f"  {label}: {truncated}")
