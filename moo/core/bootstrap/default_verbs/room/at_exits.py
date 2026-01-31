#!moo verb @exits --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to print a list of the exits in a room. It can only be used by the owner of the
room. The verb simply runs through the list of defined exits, stored in the property exits, and prints the exit name,
object reference number, destination name, and exit aliases.
"""

exits = this.get_property("exits") or []
if not exits:
    print("[color red]There are no exits defined for this room.[/color red]")
    return

print("[color cyan]Exits defined for this room:[/color cyan]")
for exit in exits:
    exit_name = exit.name
    dest_name = exit.dest.name
    aliases = ", ".join([x.alias for x in exit.aliases.all()])
    print(f"- [color yellow]{exit_name}[/color yellow] (Aliases: {aliases}) "
          f"to [color green]{dest_name}[/color green] (#{exit.dest.id})")
