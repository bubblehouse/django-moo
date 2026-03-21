#!moo verb sit_succeeded_msg osit_succeeded_msg sit_failed_msg stand_succeeded_msg ostand_succeeded_msg stand_failed_msg --on $furniture

# pylint: disable=return-outside-function,undefined-variable

"""
These verbs return a pronoun-substituted version of the corresponding message property stored on the
furniture object. They are used by `$furniture.sit` and `$player.stand`.

Property format codes:
    %N  — actor name (capitalized), resolved from context.player
    %t  — furniture name, pre-substituted from this.title() before pronoun_sub runs
    %T  — furniture name (capitalized), same
"""

prop_value = this.get_property(verb_name)

# Pre-substitute %t/%T with this.title() directly, since parser.this may not point to this
# furniture when called cross-context (e.g. from $player.stand after a no-dobj dispatch).
title = this.title()
prop_value = prop_value.replace("%T", title.capitalize()).replace("%t", title)

return _.string_utils.pronoun_sub(prop_value)
