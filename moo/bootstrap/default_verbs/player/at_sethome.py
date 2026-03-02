#!moo verb at_sethome --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to set the player's home to be the his/her current location. You can only set your
home to a room if the room will accept you, determined by checking the room's `accept` verb. This allows builders to
restrict which rooms may be used by players as their homes. If the room does not allow the player to set it as his/her
home, a suitable message is printed to inform the user of this fact. Otherwise, the player's `home` property is set to
the player's current location.
"""

from moo.core import context

player = context.player
if not player.location.accept(player):
    return "You cannot set your home to this location. It is not allowing you to enter."
player.set_property("home", player.location)
return "Your home has been set to your current location."
