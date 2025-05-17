#!moo verb say --on "player class" --dspec any

from moo.core import api, write

if not args and not api.parser.has_dobj_str():  # pylint: disable=undefined-variable  # type: ignore
    print("What do you want to say?")
    return  # pylint: disable=return-outside-function  # type: ignore

if api.parser and api.parser.has_dobj_str():
    msg = api.parser.get_dobj_str()
else:
    msg = args[0]  # pylint: disable=undefined-variable  # type: ignore

for obj in api.caller.location.contents.all():
    write(obj, f"[bright_yellow]{api.caller.name}[/bright_yellow]: {msg}")
