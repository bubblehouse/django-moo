#!moo verb leave_msg oleave_msg arrive_msg oarrive_msg nogo_msg onogo_msg --on $exit

# pylint: disable=return-outside-function,undefined-variable

"""
These verbs return a pronoun substituted version of the corresponding properties stored on the exit object. They are
used by `$exit.move`.
"""

from moo.core import api

prop_name = verb_name
prop_value = this.get_property(prop_name)
source = this.get_property("source")
dest = this.get_property("dest")
actor = api.player

if prop_name == 'nogo_msg':
    return prop_value.format(actor="You")
elif prop_name == 'onogo_msg':
    return prop_value.format(actor=actor)
elif prop_name == 'arrive_msg':
    return prop_value.format(actor="You", subject=dest)
elif prop_name == 'oarrive_msg':
    return prop_value.format(actor=actor, subject=dest)
elif prop_name == 'oleave_msg':
    return prop_value.format(actor=actor, subject=source)
elif prop_name == 'leave_msg':
    return prop_value.format(actor="You", subject=source)
else:
    raise ValueError(f"Unknown property name: {prop_name}")
