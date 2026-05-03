#!moo verb move remove goto walk perform next_sibling --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Movement helpers for ZIL games.

Generic ZIL→DjangoMOO impedance — none of these reference Zork-specific
objects.  ``walk`` does the full exit-Object traversal that the substrate
``V-WALK`` would do via Z-machine table opcodes; everything else is a
direct property/location helper that's marginally too multi-line for the
translator to inline.

move:    args[0] = object, args[1] = destination
remove:  args[0] = object  (moves to None / limbo)
goto:    args[0] = destination room  (moves context.player)
walk:    args[0] = direction string  (traverse the matching exit Object)
perform: args[0] = verb name string, args[1] = prso, args[2] = prsi
         Calls ACTION handler with explicit objects (ZIL PERFORM equivalent)
next_sibling: args[0] = object — returns the next sibling in
         ``args[0].location.contents`` (pk-ordered) or ``None``.  The ZIL
         translation of ``<NEXT? .CONT>`` calls this.
"""

from moo.sdk import context, NoSuchPropertyError


def place(target, destination):
    target.location = destination
    target.save()


if verb_name == "move":
    place(args[0], args[1])

elif verb_name == "remove":
    place(args[0], None)

elif verb_name == "goto":
    place(context.player, args[0])

elif verb_name == "walk":
    direction = args[0]
    room = context.player.location
    if room is None:
        print("You can't go that way.")
        return
    try:
        exits = room.get_property("exits")
    except NoSuchPropertyError:
        exits = []
    exit_obj = None
    for cand in exits or []:
        if cand.aliases.filter(alias=direction).exists():
            exit_obj = cand
            break
    if exit_obj is None:
        print("You can't go that way.")
        return

    try:
        dest = exit_obj.get_property("dest")
    except NoSuchPropertyError:
        dest = None
    if dest is None:
        try:
            routine_name = exit_obj.get_property("exit_routine")
        except NoSuchPropertyError:
            routine_name = None
        if routine_name:
            zthing = _.get_property("zork_thing")
            if zthing is not None and zthing.has_verb(routine_name.lower()):
                dest = zthing.invoke_verb(routine_name.lower())

    if not dest:
        try:
            print(exit_obj.get_property("nogo_msg"))
        except NoSuchPropertyError:
            try:
                exit_obj.get_property("exit_routine")  # routine printed its own block message
            except NoSuchPropertyError:
                print("You can't go that way.")
        return

    try:
        print(exit_obj.get_property("message"))
    except NoSuchPropertyError:
        pass

    context.player.location = dest
    context.player.save()

    if dest.has_verb("look_action"):
        dest.invoke_verb("look_action")
    elif dest.has_verb("look"):
        dest.invoke_verb("look")
    else:
        try:
            print(dest.get_property("description"))
        except NoSuchPropertyError:
            print(f"You enter {dest.name}.")

elif verb_name == "perform":
    verb_str = args[0]
    prso = args[1] if len(args) > 1 else None
    prsi = args[2] if len(args) > 2 else None
    if prso is not None and prso.has_verb(verb_str):
        prso.invoke_verb(verb_str, prso, prsi)

elif verb_name == "next_sibling":
    obj = args[0] if args else None
    if obj is None or obj.location is None:
        return None
    siblings = list(obj.location.contents.order_by("pk"))
    seen = False
    for sib in siblings:
        if seen:
            return sib
        if sib.pk == obj.pk:
            seen = True
    return None
