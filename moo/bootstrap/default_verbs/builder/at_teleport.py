#!moo verb teleport --on $builder --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
Teleport directly to a room by object ID or name. Equivalent to @move me to #N
but shorter and named for navigation intent. Collapses multi-step navigation
chains into a single command.

Usage:
    teleport #N       — move directly to room #N
    teleport "name"   — move directly to room by name
"""

from moo.sdk import context

if context.parser.has_pobj_str("to"):
    dest = context.parser.get_pobj("to", lookup=True)
else:
    dest = context.parser.get_dobj(lookup=True)

if not dest.is_a(_.room):
    print(f"[red]{dest.name} (#{dest.id}) is not a room.[/red]")
    return

try:
    context.player.moveto(dest)
except PermissionError:
    context.player.location.announce_all_but(
        context.player,
        f"{context.player.name} flickers violently, crackles with static, and remains exactly where they are.",
    )
    print(f"[red]Teleport failed: {dest.name} did not accept you.[/red]")
    return

print(f"You move to [bright_yellow]{dest.name}[/bright_yellow] (#{dest.id}).")
