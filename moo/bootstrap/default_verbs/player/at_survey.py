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

from moo.sdk import context, prefetch_property, NoSuchPropertyError

parser = context.parser
if parser.has_dobj_str():
    obj = parser.get_dobj(lookup=True)
else:
    obj = context.player.location

room_class = None
try:
    room_class = _.room
except Exception:  # pylint: disable=broad-except
    pass


def safe_prop(o, name, default=None):
    try:
        return o.get_property(name)
    except NoSuchPropertyError:
        return default


def render_keyexp(k):
    if isinstance(k, int):
        return f"#{k}"
    if hasattr(k, "pk"):
        return f"#{k.pk}"
    if isinstance(k, list) and k:
        op = k[0]
        if op in ("&&", "||") and len(k) == 3:
            return f"({render_keyexp(k[1])} {op} {render_keyexp(k[2])})"
        if op == "!" and len(k) == 2:
            return f"!{render_keyexp(k[1])}"
        if op == "?" and len(k) == 2:
            return f"?{render_keyexp(k[1])}"
    return str(k)


if room_class and obj.is_a(room_class):
    print(f"[bright_yellow]{obj.name}[/bright_yellow] (#{obj.id})")

    state_bits = [
        f"dark={bool(safe_prop(obj, 'dark'))}",
        f"free_entry={safe_prop(obj, 'free_entry', default=True) is not False}",
    ]
    residents = safe_prop(obj, "residents") or []
    resident_ids = [f"#{r.pk}" if hasattr(r, "pk") else f"#{r}" for r in residents]
    state_bits.append(f"residents=[{', '.join(resident_ids)}]")
    print(f"[cyan]State:[/cyan] {', '.join(state_bits)}")

    try:
        exits = obj.get_property_objects("exits", prefetch_related=["aliases"])
    except NoSuchPropertyError:
        exits = []
    if exits:
        prefetch_property(exits, "dest")
        prefetch_property(exits, "key")
        print("[cyan]Exits:[/cyan]")
        for exit_obj in exits:
            aliases = [a.alias for a in exit_obj.aliases.all()]
            direction = aliases[0] if aliases else exit_obj.name
            try:
                dest = exit_obj.get_property("dest")
                dest_str = f"{dest.name} (#{dest.id})"
            except NoSuchPropertyError:
                dest_str = "(unknown destination)"
            lock_tag = ""
            key = safe_prop(exit_obj, "key")
            if key is not None:
                lock_tag = f" (locked: {render_keyexp(key)})"
            print(f"  {direction} (#{exit_obj.id})  \u2192  {dest_str}{lock_tag}")
    contents = [o for o in obj.contents.all() if o.pk != context.player.pk]
    if contents:
        print("[cyan]Contents:[/cyan]")
        for item in contents:
            print(f"  {item.name} (#{item.id})")
else:
    print(f"[bright_yellow]{obj.name}[/bright_yellow] (#{obj.id})")
    print(f"  Location: {obj.location}")
    state_bits = [
        f"alight={bool(safe_prop(obj, 'alight'))}",
        f"opaque={safe_prop(obj, 'opaque') or 0}",
        f"open={safe_prop(obj, 'open') is True}",
    ]
    key = safe_prop(obj, "key")
    state_bits.append(f"key={render_keyexp(key) if key is not None else 'none'}")
    print(f"[cyan]State:[/cyan] {', '.join(state_bits)}")
    contents = [o for o in obj.contents.all() if o.pk != context.player.pk]
    if contents:
        print("[cyan]Contents:[/cyan]")
        for item in contents:
            print(f"  {item.name} (#{item.id})")
