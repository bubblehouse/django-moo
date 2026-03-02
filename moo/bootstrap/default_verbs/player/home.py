#!moo verb home --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is normally invoked by the player as a command. The home of a player is the room where s/he goes to when they
disconnect. Unlike some flavours of MUD, MOO does not cause you to lose all your possessions if you go home.

The `home` verb performs a simple sequence. It first checks whether the player is already at home, and tells him/her so
if this is the case. Secondly, a check is made that the player's home (stored in the `home` property on the player, is
a valid object. If this is not the case, the verb sets the home to the default, `$player_start`, and stops with a
suitable message.

Having decided that the player has a valid home s/he is not already in, the verb uses `$player.moveto` to send the
player to the home location. If this doesn't work - checked by comparing the player's home with the player's location
after the move - then for some reason the player's home location has not allowed him/her to enter. A suitable message
is printed, and no further action is taken.
"""

from moo.core import context

player = context.player
if player.get_property("home") == player.location:
    print("You are already at home.")
    return
if not player.get_property("home"):
    player.set_property("home", _.player_start)
    print("Your home was not set. It has been set to the default location.")
    return

player.moveto(player.get_property("home"))

if player.get_property("home") != player.location:
    print("You cannot go home. Your home location is not allowing you to enter.")
