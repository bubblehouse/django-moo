#!moo verb @npc --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Wizard convenience command for creating and managing NPCs.

Usage:
    @npc create <name> [from <parent>]      — synchronously create an NPC in the current room
    @npc destinations <name> [pks...]        — read or set ``wander_rooms``

For everything else (list / enable / disable / trigger / kill), NPCs are
``$daemon`` descendants, so the existing ``@daemon`` subcommands handle them.

``create`` always assigns a fresh ``Player`` record before returning, so the
new NPC reports ``is_player() == True`` immediately. The optional
``from <parent>`` defaults to ``$npc`` and accepts any descendant
(``$wanderer``, custom subclass, etc.).
"""

from moo.sdk import context, create, ensure_player_record, lookup, NoSuchObjectError, UsageError

if not context.player.is_wizard():
    print("Permission denied.")
    return

parser = context.parser
if not parser.has_dobj_str():
    raise UsageError("Usage: @npc create <name> [from <parent>]  |  @npc destinations <name> [pks...]")

words = parser.get_dobj_str().split()
sub = words[0].lower()

if sub == "create":
    if len(words) < 2:
        raise UsageError("Usage: @npc create <name> [from <parent>]")
    parent_name = "$npc"
    if parser.has_pobj_str("from"):
        parent_name = parser.get_pobj_str("from")
        name = " ".join(words[1:])
    else:
        name = " ".join(words[1:])
    try:
        parent_obj = lookup(parent_name)
    except NoSuchObjectError:
        print(f"No such parent: {parent_name!r}")
        return
    npc_cls = lookup("Generic NPC")
    if not parent_obj.is_a(npc_cls) and parent_obj != npc_cls:
        print(f"{parent_obj.name} is not an $npc descendant.")
        return
    npc = create(name, parents=[parent_obj], location=context.player.location)
    ensure_player_record(npc)
    print(f"Created {npc.name} (#{npc.pk}) from {parent_obj.name}.")
    return

if sub == "destinations":
    if len(words) < 2:
        raise UsageError("Usage: @npc destinations <name> [pks...]")
    name = words[1]
    try:
        npc = lookup(name)
    except NoSuchObjectError:
        print(f"No such NPC: {name!r}")
        return
    if len(words) == 2:
        rooms = npc.get_property("wander_rooms") or []
        if not rooms:
            print(f"{npc.name} has no destinations.")
            return
        labels = []
        for pk in rooms:
            try:
                r = lookup(pk)
                labels.append(f"#{r.pk} ({r.name})")
            except NoSuchObjectError:
                labels.append(f"#{pk} (missing)")
        print(f"{npc.name} destinations: {', '.join(labels)}")
        return
    new_pks = []
    for tok in words[2:]:
        tok = tok.lstrip("#")
        if not tok.isdigit():
            print(f"Skipping non-numeric pk: {tok!r}")
            continue
        new_pks.append(int(tok))
    npc.set_property("wander_rooms", new_pks)
    print(f"{npc.name} destinations set to {new_pks}.")
    return

print(f"Unknown @npc subcommand {sub!r}. Try: create, destinations.")
