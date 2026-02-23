#!moo verb throw drop --on $thing --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
One or the other of these verbs is invoked when a player tries to place an object in the room s/he is currently
located, i.e., when the player tries to drop the object. Again, the code is fairly straightforward. If the object is
not located on the player, then a suitable message is sent to the player telling him/her to check his/her pockets. If
the player does possess the object, and the current location `accept` verb indicates that the room will allow the
object to be dropped, the object `moveto` verb is invoked to move the object from the player's inventory to the
contents list of the player's location. Suitable messages are printed to inform the player that the action succeeded,
and to tell other people in the room that the object has just been dropped.
"""

from moo.core import api

if this.location != api.player:
    print("You check your pockets, but can't find {}.".format(this.title()))
elif this.location.accept(this):
    this.moveto(api.player.location)
    print(this.drop_succeeded_msg().format(actor="You", subject=this))
    if msg := this.odrop_succeeded_msg():
        this.location.announce(msg.format(actor=api.player, subject=this))
else:
    print(this.drop_failed_msg().format(actor="You", subject=this))
    if msg := this.odrop_failed_msg():
        this.location.announce(msg.format(actor=api.player, subject=this))
