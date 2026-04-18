#!moo verb @burrow --on $builder --dspec any --ispec "to:any"

# pylint: disable=return-outside-function,undefined-variable

"""
Atomic bidirectional dig. Creates a forward exit, a new destination room, moves the
caller into it, and creates the return exit automatically — all in one command.
The return direction is inferred as the opposite of the forward direction.

Reduces the three fallible steps (@dig + go + @tunnel) to a single atomic operation,
eliminating the most common source of "exit wired in only one direction" bugs.

Usage:
    @burrow north to "The Watchtower"

Output:
    Dug north to The Watchtower (#81).
    Tunnelled south back to The Laboratory (#19).
    You are now in The Watchtower (#81).
"""

from moo.sdk import context, create, OPPOSITE_DIRECTIONS

OPPOSITES = OPPOSITE_DIRECTIONS

parser = context.parser
direction = parser.get_dobj_str()
dest_name = parser.get_pobj_str("to")
return_direction = OPPOSITES.get(direction.lower())

source = context.player.location

if source.match_exit(direction):
    print(f"[red]There is already an exit {direction} from this room.[/red]")
    return

# Create forward door and destination room (same logic as @dig)
forward_door = create(f"{direction} from {source.name}", parents=[_.exit], location=None)
forward_door.add_alias(direction)
dest = create(dest_name, parents=[_.room], location=None)
forward_door.set_property("source", source)
forward_door.set_property("dest", dest)
source.add_exit(forward_door)
dest.add_entrance(forward_door)

print(f"[yellow]Dug {direction} to {dest.name} (#{dest.pk}).[/yellow]")

# Move player into new room
context.player.moveto(dest)

if not return_direction:
    print(
        f"[yellow]Note: no automatic return direction for '{direction}'. Use @tunnel to wire the return exit.[/yellow]"
    )
    print(f"You are now in [bright_yellow]{dest.name}[/bright_yellow] (#{dest.pk}).")
    return

# Check return direction is free
if dest.match_exit(return_direction):
    print(f"[red]There is already an exit {return_direction} in {dest.name}. Return exit not created.[/red]")
    print(f"You are now in [bright_yellow]{dest.name}[/bright_yellow] (#{dest.pk}).")
    return

# Create return door (same logic as @tunnel)
return_door = create(f"{return_direction} from {dest.name}", parents=[_.exit], location=None)
return_door.add_alias(return_direction)
return_door.set_property("source", dest)
return_door.set_property("dest", source)
dest.add_exit(return_door)
source.add_entrance(return_door)

print(f"[yellow]Tunnelled {return_direction} back to {source.name} (#{source.pk}).[/yellow]")
print(f"You are now in [bright_yellow]{dest.name}[/bright_yellow] (#{dest.pk}).")
