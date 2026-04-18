#!moo verb @recycle --on $builder --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to recycle an object. This simply matches the dobjstr with an object, and calls the
delete() method to recycle the object. The returned value, in the case of an error, is printed to the player. Otherwise,
a suitable success message is sent.
"""

from moo.sdk import context

if not context.parser.has_dobj_str():
    print("[yellow]What do you want to recycle?[/yellow]")
    return

obj = context.parser.get_dobj()
name = obj.title()
try:
    obj.delete()
    print(f"[yellow]Recycled {name}.[/yellow]")
except Exception:  # pylint: disable=broad-exception-caught
    print(f"[red]Error recycling {name}.[/red]")
