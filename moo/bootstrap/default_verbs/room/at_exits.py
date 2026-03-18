#!moo verb @exits --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Print a list of the exits in a room. It can only be used by the owner of the
room. The verb simply runs through the list of defined exits, stored in the property exits, and prints the exit name,
object reference number, destination name, and exit aliases.
"""

exits = this.get_property_objects("exits", prefetch_related=["aliases"]) or []
if not exits:
    print("[red]There are no exits defined for this room.[/red]")
    return

print("[cyan]Exits defined for this room:[/cyan]")
for exit_obj in exits:
    exit_name = exit_obj.name
    dest_name = exit_obj.dest.name
    aliases = ", ".join([x.alias for x in exit_obj.aliases.all()])
    print(
        f"- [yellow]{exit_name}[/yellow] (Aliases: {aliases}) " f"to [green]{dest_name}[/green] (#{exit_obj.dest.id})"
    )
