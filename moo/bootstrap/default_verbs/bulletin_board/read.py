#!moo verb r*ead --on $bulletin_board --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Display all current entries on the bulletin board, numbered.
Any player may read. Usage: read <board>
"""

entries = this.get_property("entries") or []
if not entries:
    print("The board is blank.")
    return
for i, e in enumerate(entries, 1):
    print(f"  {i}. {e}")
