#!moo verb g*et take --on $player --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is called in the situation when another object tries to get or take a player. Given that this is a fairly
nonsensical thing to do, it is not allowed. Suitable messages are sent to the object that invoked the action, and
the player object.
"""

from moo.core import context

player = context.player
print("You can't take a player!")
player.tell(_.sprintf("%N tried unsucessfully to take you."))
