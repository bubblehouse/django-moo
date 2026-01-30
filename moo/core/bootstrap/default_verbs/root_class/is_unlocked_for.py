#!moo verb is_unlocked_for --on $root_class

# pylint: disable=return-outside-function,undefined-variable

"""
Returns `True` if the object is unlocked for the argument. If the value of this.key is None, the object is unlocked. If
this is not the case. the verb $lock_utils:eval_key() is used to determine the result.
"""

thing = args[0]

if not this.key:
    return True

return _.lock_utils.eval_key(this.key, thing)
