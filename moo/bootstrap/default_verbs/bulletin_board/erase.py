#!moo verb er*ase --on $bulletin_board --dspec this --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove all entries whose text contains the given key string.
Only the board's owner or a wizard may erase.
Usage: erase <board> from "<key>"
"""

from moo.sdk import context, lookup

wizard = lookup(1).wizard
if context.player != this.owner and not context.player.is_a(wizard):
    print("You don't have permission to erase entries from this board.")
    return

key = context.parser.get_pobj_str("from")
entries = this.get_property("entries") or []
before = len(entries)
entries = [e for e in entries if key not in e]
this.set_property("entries", entries)
removed = before - len(entries)
print(f"Erased {removed} entr{'y' if removed == 1 else 'ies'} containing '{key}'.")
