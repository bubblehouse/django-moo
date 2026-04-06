#!moo verb @survey --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Lightweight room inspector for agents. Returns only what agents need: exits with destination
object IDs, and a flat contents list. Produces ~5 lines per room instead of the ~40 lines
that @show here generates, preventing context overload in long sessions.

Usage:
    @survey       — survey the current room
    @survey here  — same as above
    @survey #N    — survey room or object by object ID
"""

from moo.sdk import context, NoSuchPropertyError

parser = context.parser
if parser.has_dobj_str():
    obj = parser.get_dobj(lookup=True)
else:
    obj = context.player.location

system = context.player.location
room_class = None
try:
    room_class = _.room
except Exception:  # pylint: disable=broad-except
    pass

if room_class and obj.is_a(room_class):
    print(f"[bright_yellow]{obj.name}[/bright_yellow] (#{obj.id})")
    try:
        exits = obj.get_property_objects("exits", prefetch_related=["aliases"])
    except NoSuchPropertyError:
        exits = []
    if exits:
        print("[cyan]Exits:[/cyan]")
        for exit_obj in exits:
            aliases = [a.alias for a in exit_obj.aliases.all()]
            direction = aliases[0] if aliases else exit_obj.name
            try:
                dest = exit_obj.get_property("dest")
                dest_str = f"{dest.name} (#{dest.id})"
            except (NoSuchPropertyError, Exception):  # pylint: disable=broad-except
                dest_str = "(unknown destination)"
            print(f"  {direction}  \u2192  {dest_str}")
    contents = [o for o in obj.contents.all() if o.pk != context.player.pk]
    if contents:
        print("[cyan]Contents:[/cyan]")
        for item in contents:
            print(f"  {item.name} (#{item.id})")
else:
    print(f"[bright_yellow]{obj.name}[/bright_yellow] (#{obj.id})")
    print(f"  Location: {obj.location}")
    contents = [o for o in obj.contents.all() if o.pk != context.player.pk]
    if contents:
        print("[cyan]Contents:[/cyan]")
        for item in contents:
            print(f"  {item.name} (#{item.id})")
