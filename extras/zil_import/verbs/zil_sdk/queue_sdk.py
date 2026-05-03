#!moo verb queue cancel --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Turn-based interrupt queue for Zork daemons (ZIL ENABLE/DISABLE).

queue:  args[0] = routine name string, args[1] = delay in turns
cancel: args[0] = routine name string

The queue is stored per-player as "zstate_queue" (list of dicts).
confunc increments zstate_moves and fires routines whose fire_at_turn is due.
"""

from moo.sdk import context, NoSuchPropertyError

routine_name = args[0]
try:
    queue = context.player.get_property("zstate_queue")
except NoSuchPropertyError:
    queue = []
if queue is None:
    queue = []
# Drop any existing entry for this routine — both cancel and re-queue paths
# remove the old one first.
queue = [entry for entry in queue if entry.get("name") != routine_name]

if verb_name == "queue":
    delay = args[1] if len(args) > 1 else 1
    try:
        moves = context.player.get_property("zstate_moves")
    except NoSuchPropertyError:
        moves = 0
    if moves is None:
        moves = 0
    queue.append({"name": routine_name, "fire_at_turn": moves + delay})

context.player.set_property("zstate_queue", queue)
