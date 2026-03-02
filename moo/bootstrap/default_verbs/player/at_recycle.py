#!moo verb @recycle --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to recycle an object. This simply matches the dobjstr with an object, and calls the
delete() method to recycle the object. The returned value, in the case of an error, is printed to the player. Otherwise,
a suitable success message is sent.
"""

from moo.core import context

if not context.parser.has_dobj_str():
    print("[color yellow]What do you want to recycle?[/color yellow]")
    return

obj = context.parser.get_dobj()
name = obj.title()
try:
    obj.delete()
    print(f"[color yellow]Recycled {name}.[/color yellow]")
except Exception:
    print(f"[color red]Error recycling {name}.[/color red]")
