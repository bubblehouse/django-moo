#!moo verb stand --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Stand up from whatever the player is currently sitting on. Because this verb lives on `$player`
rather than `$furniture`, it works in any room regardless of whether furniture is present.

Usage:
    stand              — stand up from whatever you're sitting on
    stand <furniture>  — stand up from a specific piece of furniture (validates you're on it)
"""

from moo.sdk import context, NoSuchPropertyError, NoSuchObjectError

player = context.player

try:
    seated_on = player.get_property("seated_on")
except NoSuchPropertyError:
    seated_on = None

if context.parser.has_dobj():
    try:
        target = context.parser.get_dobj()
    except NoSuchObjectError:
        print("You don't see that here.")
        return
    if seated_on != target:
        print(target.stand_failed_msg())
        return
    player.set_property("seated_on", None)
    print(target.stand_succeeded_msg())
    if msg := target.ostand_succeeded_msg():
        target.location.announce(msg)
    return

if seated_on is None:
    print("You aren't sitting on anything.")
    return

furniture = seated_on
player.set_property("seated_on", None)
print(furniture.stand_succeeded_msg())
if msg := furniture.ostand_succeeded_msg():
    furniture.location.announce(msg)
