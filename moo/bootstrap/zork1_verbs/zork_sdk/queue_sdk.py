#!moo verb queue cancel --on $zork_sdk
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

if verb_name == "cancel":
    try:
        queue = context.player.get_property("zstate_queue") or []
    except NoSuchPropertyError:
        queue = []
    queue = [entry for entry in queue if entry.get("name") != routine_name]
    context.player.set_property("zstate_queue", queue)
else:
    delay = args[1] if len(args) > 1 else 1
    try:
        moves = context.player.get_property("zstate_moves") or 0
    except NoSuchPropertyError:
        moves = 0
    try:
        queue = context.player.get_property("zstate_queue") or []
    except NoSuchPropertyError:
        queue = []
    # Remove any existing entry for this routine before re-queuing
    queue = [entry for entry in queue if entry.get("name") != routine_name]
    queue.append({"name": routine_name, "fire_at_turn": moves + delay})
    context.player.set_property("zstate_queue", queue)
