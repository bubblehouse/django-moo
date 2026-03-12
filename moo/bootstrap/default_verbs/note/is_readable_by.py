#!moo verb is_readable_by --on $note

# pylint: disable=return-outside-function,undefined-variable

"""
This verb uses the `$lock_utils.eval_key` verb to evaluate the key, stored in the `read_key` property, and determine if
the note is readable or not by the player. This verb will return `True` if it is readable, or `False` if it is not.
"""

player = args[0]

if not this.read_key:
    return True

return _.lock_utils.eval_key(this.read_key, player)
