#!moo verb otake_succeeded_msg otake_failed_msg take_succeeded_msg take_failed_msg odrop_succeeded_msg odrop_failed_msg drop_succeeded_msg drop_failed_msg --on $thing

# pylint: disable=return-outside-function,undefined-variable

"""
These verbs return a pronoun-substituted version of the corresponding message property stored on the
thing object. They are used by `$thing.take` and `$thing.drop`.

Property format codes:
    %N  — actor name (capitalized), resolved from context.player
    %t  — object name, pre-substituted from this.title() before pronoun_sub runs
    %T  — object name (capitalized), same
"""

prop_value = this.get_property(verb_name)

# Pre-substitute %t/%T with this.title() directly so the object name is always correct
# regardless of what parser.this points to at the call site.
title = this.title()
prop_value = prop_value.replace("%T", title.capitalize()).replace("%t", title)

return _.string_utils.pronoun_sub(prop_value)
