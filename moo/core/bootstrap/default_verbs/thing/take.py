#!moo verb take get --on $thing --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
One or the other of these verbs is invoked when a player tries to take possession of an object i.e., pick it up. The
code involved is fairly straightforward. It checks to see if the player already has the object, and prints a suitable
message if this is the case. If not, then the `moveto` verb on the object is invoked. If this results in the object
moving into the player's inventory, then the take_succeeded messages defined on the object are printed. If the `moveto`
failed, then the `*take_failed` messages for the object are printed.

This scheme allows you to add extra conditions to restrict whether a player can take an object or not. For example, you
may place a notion of strength onto a player, and add weight to objects. If an object is too heavy for a player to lift,
then the object cannot be taken by the player. This sort of condition should be added to the `take` verb for the object
"""

from moo.core import api

if this.location == api.player:
    print("You already have {} in your inventory.".format(this.title()))
elif this.moveto(api.player):
    print(this.take_succeeded_msg().format(actor="You", subject=this))
    if msg := this.otake_succeeded_msg():
        this.location.announce(msg.format(actor=api.player, subject=this))
else:
    print(this.take_failed_msg().format(actor="You", subject=this))
    if msg := this.otake_failed_msg():
        this.location.announce(msg.format(actor=api.player, subject=this))
