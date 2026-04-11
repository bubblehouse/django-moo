#!moo verb p*ost --on $bulletin_board --dspec none --ispec on:this --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Append a one-line entry to the bulletin board, tagged with the posting player's name.
Any player may post. Usage: post on <board> with "text"
"""

from moo.sdk import context

text = context.parser.get_pobj_str("with")
entries = this.get_property("entries") or []
entries.append(f"{context.player.name}: {text}")
this.set_property("entries", entries)
print("Posted.")
