#!moo verb p*ost --on $bulletin_board --dspec none --ispec on:this --ispec with:any --ispec under:any

# pylint: disable=return-outside-function,undefined-variable

"""
Post to the bulletin board.

Usage:
    post on <board> with "text"                     — append a general entry tagged with your name
    post on <board> under <topic> with "text"         — store text under a topic key (overwrites)
"""

from moo.sdk import context

text = context.parser.get_pobj_str("with")

if context.parser.has_pobj_str("under"):
    topic = context.parser.get_pobj_str("under").strip().lower()
    topics = this.get_property("topics") or {}
    topics[topic] = text
    this.set_property("topics", topics)
    print(f"Posted to topic '{topic}'.")
else:
    entries = this.get_property("entries") or []
    entries.append(f"{context.player.name}: {text}")
    this.set_property("entries", entries)
    print("Posted.")
