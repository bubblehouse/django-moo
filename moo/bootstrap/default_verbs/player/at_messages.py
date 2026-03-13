#!moo verb @messages --on $player --dspec any

"""
This is a player command used to list the possible message properties (those that end in ``_msg``) on the dobjstr
supplied. The names of the messages, along with their current values, are displayed.
"""

from moo.core import context, lookup

parser = context.parser
if parser.has_dobj():
    obj = parser.get_dobj()
else:
    obj = parser.get_dobj(lookup=True)

for prop in obj.properties.all():
    if prop.name.endswith('_msg'):
        print(f"{prop.name}: {prop.value}")
