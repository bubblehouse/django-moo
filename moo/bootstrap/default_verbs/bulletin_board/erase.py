#!moo verb er*ase --on $bulletin_board --dspec this --ispec under:any

# pylint: disable=return-outside-function,undefined-variable

"""
Erase entries from the bulletin board. Only the board's owner or a wizard may erase.

Usage:
    erase <board> under <topic>   — remove the value stored under that topic
    erase <board>               — clear all general entries
"""

from moo.sdk import context, lookup

wizard = lookup(1).wizard
if context.player != this.owner and not context.player.is_a(wizard):
    print("You don't have permission to erase entries from this board.")
    return

if context.parser.has_pobj_str("under"):
    topic = context.parser.get_pobj_str("under").strip().lower()
    topics = this.get_property("topics") or {}
    if topic in topics:
        topics.pop(topic)
        this.set_property("topics", topics)
        print(f"Topic '{topic}' erased.")
    else:
        print(f"No topic '{topic}' found.")
else:
    this.set_property("entries", [])
    print("Board cleared.")
