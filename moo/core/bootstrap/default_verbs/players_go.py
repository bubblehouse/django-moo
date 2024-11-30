#!moo verb go --on "author class" --ability

from moo.core import api

direction = api.parser.get_dobj_str()

if api.caller.location.has_property('exits'):
    exits = api.caller.location.get_property('exits')
else:
    exits = {}

if direction not in exits:
    print(f'[color red]There is no exit in that direction.[/color]')
    return # pylint: disable=return-outside-function  # type: ignore

exit_info = exits[direction]
destination = exit_info['destination']
door = exit_info.get('door')

if door and not door.invoke_verb('open?'):
    print(f'[color red]The {door.name} is closed.[/color]')
    return # pylint: disable=return-outside-function  # type: ignore

api.caller.location = destination
print(f'You go {direction}.')