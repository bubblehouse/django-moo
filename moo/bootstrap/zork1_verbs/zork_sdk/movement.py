#!moo verb move remove goto walk perform --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Movement helpers for Zork verbs.

move:    args[0] = object, args[1] = destination
remove:  args[0] = object  (moves to None / limbo)
goto:    args[0] = destination room  (moves context.player)
walk:    args[0] = direction string  (invokes exit for that direction)
perform: args[0] = verb name string, args[1] = prso, args[2] = prsi
         Calls ACTION handler with explicit objects (ZIL PERFORM equivalent)
"""

from moo.sdk import context, NoSuchPropertyError


def place(obj, dest):
    obj.location = dest
    obj.save()


if verb_name == "move":
    place(args[0], args[1])

elif verb_name == "remove":
    place(args[0], None)

elif verb_name == "goto":
    place(context.player, args[0])

elif verb_name == "walk":
    direction = args[0]
    loc = context.player.location
    try:
        exits = loc.get_property("exits")
    except NoSuchPropertyError:
        exits = []
    for exit_obj in exits:
        if exit_obj.aliases.filter(alias=direction).exists():
            exit_obj.invoke_verb("move", context.player)
            return
    print("You can't go that way.")

elif verb_name == "perform":
    verb_str = args[0]
    prso = args[1] if len(args) > 1 else None
    prsi = args[2] if len(args) > 2 else None
    if prso is not None and prso.has_verb(verb_str):
        prso.invoke_verb(verb_str, prso, prsi)
