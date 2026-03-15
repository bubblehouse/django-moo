#!moo verb otake_succeeded_msg otake_failed_msg take_succeeded_msg take_failed_msg odrop_succeeded_msg odrop_failed_msg drop_succeeded_msg drop_failed_msg --on $thing

# pylint: disable=return-outside-function,undefined-variable

"""
These verbs return a pronoun substituted version of the corresponding properties stored on the thing object. They are
used by `$thing.take` and `$thing.drop`.
"""

from moo.sdk import context

prop_name = verb_name
prop_value = this.get_property(prop_name)
actor = context.player
subject = args[0] if len(args) > 0 else this.title()

if prop_name == 'take_succeeded_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(subject))
elif prop_name == 'otake_failed_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(subject))
elif prop_name == 'otake_succeeded_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(subject))
elif prop_name == 'take_failed_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(subject))
elif prop_name == 'odrop_succeeded_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(subject))
elif prop_name == 'odrop_failed_msg':
    return prop_value.replace("{actor}", str(actor)).replace("{subject}", str(subject))
elif prop_name == 'drop_succeeded_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(subject))
elif prop_name == 'drop_failed_msg':
    return prop_value.replace("{actor}", "You").replace("{subject}", str(subject))
else:
    raise ValueError(f"Unknown property name: {prop_name}")
