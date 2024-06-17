from moo.core import api

if not api.parser.has_dobj_str():
    print("What do you want to say?")
    return  # pylint: disable=return-outside-function  # type: ignore

for obj in api.caller.location.contents.all():
    msg = api.parser.get_dobj_str()
    message_user(obj, f"[bright_yellow]{api.caller.name}[/bright_yellow]: {msg}")  # pylint: disable=undefined-variable