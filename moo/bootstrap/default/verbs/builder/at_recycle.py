#!moo verb @recycle --on $builder --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Recycle an object.  As of spec 200 (item K) this is a *non-destructive*
soft-recycle: the object's quota is refunded and it is hidden from the world,
but its id and inbound references are kept so ``@restore`` can bring it back.
Use ``@destroy`` for permanent removal.
"""

from moo.sdk import context, soft_recycle

if not context.parser.has_dobj_str():
    print("[yellow]What do you want to recycle?[/yellow]")
    return

obj = context.parser.get_dobj(lookup=True)
name = obj.title()
try:
    soft_recycle(obj)
    print(f"[yellow]Recycled {name}. Use @restore to recover it.[/yellow]")
except Exception:  # pylint: disable=broad-exception-caught
    print(f"[red]Error recycling {name}.[/red]")
