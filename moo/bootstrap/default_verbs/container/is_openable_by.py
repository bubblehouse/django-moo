#!moo verb is_openable_by --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb uses the `$lock_utils.eval_key` verb to determine if the container can be opened by the player. It will
return `True` if the player has permission to open the container, and `False` otherwise
"""

player = args[0]

return _.lock_utils.eval_key(this.open_key, player)
