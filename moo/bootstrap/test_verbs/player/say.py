#!moo verb say --on "player class" --dspec any

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context, write

if not args and not context.parser.has_dobj_str():  # pylint: disable=undefined-variable  # type: ignore
    print("What do you want to say?")
    return  # pylint: disable=return-outside-function  # type: ignore

if context.parser and context.parser.has_dobj_str():
    msg = context.parser.get_dobj_str()
else:
    msg = args[0]  # pylint: disable=undefined-variable  # type: ignore

for obj in context.caller.location.contents.all():
    write(obj, f"[color bright_yellow]{context.caller.name}[/color bright_yellow]: {msg}")
