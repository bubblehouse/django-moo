#!moo verb jigs_up --on "System Object"
# pylint: disable=return-outside-function,undefined-variable
"""
Kill the player: print death message and respawn at starting room.

args[0] = death message string
player_start is stored on the System Object (this) as world config.
"""

from moo.sdk import context

print(args[0])
start = this.get_property("player_start")
context.player.location = start
context.player.save()
print("\n**** You have died ****\n")
context.player.zstate_set("DEATHS", (context.player.zstate_get("DEATHS") or 0) + 1)
