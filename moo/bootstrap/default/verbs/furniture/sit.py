#!moo verb sit --on $furniture --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Sit on a piece of furniture. Tracks the player's seated state via a `seated_on` property on the
player object. The player must stand up before sitting on a different piece of furniture.

Usage:
    sit <furniture>
"""

from moo.sdk import context, NoSuchPropertyError

player = context.player

try:
    seated_on = player.get_property("seated_on")
    if seated_on == this:
        print(this.sit_failed_msg())
        return
    print("You're already sitting down.")
    return
except NoSuchPropertyError:
    pass

player.set_property("seated_on", this)
print(this.sit_succeeded_msg())
if msg := this.osit_succeeded_msg():
    this.location.announce(msg)
