#!moo verb leave_msg oleave_msg arrive_msg oarrive_msg nogo_msg onogo_msg --on $exit

# pylint: disable=return-outside-function,undefined-variable

"""
These verbs return a pronoun substituted version of the corresponding properties stored on the exit object. They are
used by `$exit.move`.
"""

from moo.core import context

prop_name = verb_name
prop_value = this.get_property(prop_name)
source = args[0] if len(args) > 0 else this.get_property("source")
dest = args[1] if len(args) > 1 else this.get_property("dest")
actor = context.player

if prop_name == 'nogo_msg':
    return prop_value.replace("{actor}", "You")
elif prop_name == 'onogo_msg':
    return prop_value.replace("{actor}", str(actor))
elif prop_name == 'arrive_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(dest))
elif prop_name == 'oarrive_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(dest))
elif prop_name == 'oleave_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(source))
elif prop_name == 'leave_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(source))
else:
    raise ValueError(f"Unknown property name: {prop_name}")
