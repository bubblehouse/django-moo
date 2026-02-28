#!moo verb gag_p --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb returns `True` if the current value of the `player` variable is in the gag list of the object indicated by
the variable `this`, or if a non-player object mentioned in the gag list is in the first elements of the verb's
`context.caller_stack` list.
"""

from moo.core import context

player = context.player
gaglist = this.gaglist

for item in gaglist:
    if item == player:
        return True
    if not item.is_player():
        for frame in context.caller_stack:
            if frame["caller"] == item:
                return True
return False
