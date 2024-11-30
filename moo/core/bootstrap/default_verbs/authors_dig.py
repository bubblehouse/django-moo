#!moo verb dig --on "author class" --ability

from moo.core import api, create, lookup

directions = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest', 'up', 'down']

direction = api.parser.get_dobj_str()

if api.parser.has_pobj('through'):
    door = api.parser.get_pobj('through')
else:
    door = None

if api.caller.location.has_property('exits'):
    exits = api.caller.location.get_property('exits')
else:
    exits = {}

if direction in exits:
    print(f'[color red]There is already an exit in that direction.[/color]')
    return # pylint: disable=return-outside-function  # type: ignore

room_class = lookup('room class')
room = create(api.parser.get_pobj_str('to'), parents=[room_class])

exits[direction] = {
    'door': door,
    'destination': room
}

api.caller.location.set_property('exits', exits)