#!moo verb @restore --on $builder --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Restore a soft-recycled object (spec 200, item K).  ``@restore`` with no
argument lists your recycled objects; ``@restore <name>`` or ``@restore #<id>``
brings one back.  Recycled objects are hidden from the normal parser, so this
verb searches them explicitly.
"""

from moo.sdk import context, get_recycled, restore

if not context.parser.has_dobj_str():
    recycled = get_recycled(owner=context.player)
    if not recycled:
        print("You have nothing to restore.")
        return
    print("[yellow]Recycled objects you can @restore:[/yellow]")
    for o in recycled:
        print(f"  #{o.id} {o.name}")
    return

target = context.parser.get_dobj_str()
match = None
for o in get_recycled():
    if target.startswith("#") and target[1:].isdigit() and o.id == int(target[1:]):
        match = o
        break
    if o.name.lower() == target.lower():
        match = o
        break

if match is None:
    print(f"[red]No recycled object matching {target!r}.[/red]")
    return

name = match.name
restore(match)
print(f"[green]Restored {name} (#{match.id}).[/green]")
