#!moo verb @entrances --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
List the entrances to the player's current location. Only the owner of a room may
list it's entrances. For every object kept in the room's entrances list, the exit name, object reference number and
aliases are displayed to the player.
"""

entrances = this.get_property_objects("entrances", prefetch_related=["aliases"]) or []
if not entrances:
    print("[red]There are no entrances defined for this room.[/red]")
    return

print("[cyan]Entrances defined for this room:[/cyan]")
for exit_obj in entrances:
    exit_name = exit_obj.name
    dest_name = exit_obj.dest.name
    aliases = ", ".join([x.alias for x in exit_obj.aliases.all()])
    print(f"- [yellow]{exit_name}[/yellow] (Aliases: {aliases}) to [green]{dest_name}[/green] (#{exit_obj.dest.id})")
