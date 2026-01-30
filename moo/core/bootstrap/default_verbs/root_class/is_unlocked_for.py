#!moo verb is_unlocked_for --on "Root Class"

"""
Returns `True` if the object is unlocked for the argument. If the value of this.key is None, the object is unlocked. If
this is not the case. the verb $lock_utils:eval_key() is used to determine the result.
"""

thing = args[0]

if not this.key:
    return True  # pylint: disable=return-outside-function. # type: ignore

return _.lock_utils.eval_key(this.key, thing)  # pylint: disable=return-outside-function. # type: ignore
