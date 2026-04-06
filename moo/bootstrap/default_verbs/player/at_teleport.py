#!moo verb teleport --on $player --dspec any

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

dest = context.parser.get_dobj(lookup=True)

if not dest.is_a(_.room):
    print(f"[red]{dest.name} (#{dest.id}) is not a room.[/red]")
    return

context.player.moveto(dest)
print(f"You move to [bright_yellow]{dest.name}[/bright_yellow] (#{dest.id}).")
