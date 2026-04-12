#!moo verb jigs_up --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Kill the player: print death message and respawn at starting room.

args[0] = death message string
player_start is stored on $zork_sdk (this) as world config.
"""

from moo.sdk import context

print(args[0])
start = this.get_property("player_start")
context.player.location = start
context.player.save()
print("\n**** You have died ****\n")
_.zork_sdk.zstate_set("DEATHS", (_.zork_sdk.zstate_get("DEATHS") or 0) + 1)
