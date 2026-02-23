#!moo verb @entrances --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to list the entrances to the player's current location. Only the owner of a room may
list it's entrances. For every object kept in the room's entrances list, the exit name, object reference number and
aliases are displayed to the player.
"""

entrances = this.get_property("entrances") or []
if not entrances:
    print("[color red]There are no entrances defined for this room.[/color red]")
    return

print("[color cyan]Entrances defined for this room:[/color cyan]")
for exit in entrances:
    exit_name = exit.name
    dest_name = exit.dest.name
    aliases = ", ".join([x.alias for x in exit.aliases.all()])
    print(f"- [color yellow]{exit_name}[/color yellow] (Aliases: {aliases}) "
          f"to [color green]{dest_name}[/color green] (#{exit.dest.id})")
