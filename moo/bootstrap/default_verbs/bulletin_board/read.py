#!moo verb r*ead --on $bulletin_board --dspec this --ispec under:any

# pylint: disable=return-outside-function,undefined-variable

"""
Display entries on the bulletin board.

Usage:
    read <board>                — show all general entries and posted topics
    read <board> under <topic>    — show the value stored under that topic
"""

from moo.sdk import context

topics = this.get_property("topics") or {}
entries = this.get_property("entries") or []

if context.parser.has_pobj_str("under"):
    topic = context.parser.get_pobj_str("under").strip().lower()
    if topic in topics:
        print(f"[{topic}] {topics[topic]}")
    else:
        print(f"Nothing posted for topic '{topic}'.")
    return

if not entries and not topics:
    print("The board is blank.")
    return

for i, e in enumerate(entries, 1):
    print(f"  {i}. {e}")

for topic, value in topics.items():
    print(f"  [{topic}] {value}")
