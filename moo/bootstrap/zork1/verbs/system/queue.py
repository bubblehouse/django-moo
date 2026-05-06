#!moo verb queue cancel tick --on "System Object"
# pylint: disable=return-outside-function,undefined-variable
"""
Turn-based interrupt queue for Zork daemons (ZIL ENABLE/DISABLE).

queue:  args[0] = routine name string, args[1] = delay in turns
cancel: args[0] = routine name string
tick:   no args.  Increments ``zstate_moves`` and fires any queued
        routine whose ``fire_at_turn`` has been reached.  Replacement
        for ZIL's CLOCKER, which uses Z-machine table primitives we
        don't translate.  Called from ``system/do_command.py`` post-
        preturnfunc so daemons fire on every player command.

The queue is stored per-player as "zstate_queue" (list of dicts).
"""

from moo.sdk import context, NoSuchPropertyError

if verb_name == "tick":
    try:
        moves = context.player.get_property("zstate_moves")
    except NoSuchPropertyError:
        moves = 0
    if moves is None:
        moves = 0
    moves += 1
    context.player.set_property("zstate_moves", moves)

    try:
        queue = context.player.get_property("zstate_queue")
    except NoSuchPropertyError:
        queue = []
    if not queue:
        return

    # Partition: routines whose timer is up versus those still waiting.
    # The original queue persists with the survivors; we fire the rest.
    due = [e for e in queue if e.get("fire_at_turn", 0) <= moves]
    pending = [e for e in queue if e.get("fire_at_turn", 0) > moves]
    context.player.set_property("zstate_queue", pending)

    # Fire each due routine.  The routines may re-queue themselves
    # (i-river does this each tick), in which case the new entry is
    # appended to ``pending`` via the ``queue`` verb and survives.
    #
    # Some daemons (e.g. ``i-forest-room``, ``i-thief``) reference
    # routines that don't translate cleanly — predicates like
    # ``forest_room_p`` aren't defined.  Catch per-daemon failures so
    # one broken daemon doesn't take down every command.
    zthing = _.get_property("zork_thing")
    if zthing is None:
        return
    for entry in due:
        name = entry.get("name")
        if not name:
            continue
        # Daemons are queued under their ZIL atom (UPPER-KEBAB or
        # lower-kebab like ``i-river``); the verb registry stores them
        # snake-cased (``i_river``) per the translator's identifier
        # sanitization.  Convert kebab → snake before lookup.
        verb = name.lower().replace("-", "_")
        if zthing.has_verb(verb):
            try:
                zthing.invoke_verb(verb)
            except Exception:  # pylint: disable=broad-except
                # Drop the broken daemon — re-queueing it would just
                # crash on the next tick.  A future Phase 3 fix will
                # make these daemons translate cleanly; until then,
                # one crash is enough to kill them.
                pass
    return

# queue / cancel paths: both first remove the existing entry by name.
routine_name = args[0]
try:
    queue = context.player.get_property("zstate_queue")
except NoSuchPropertyError:
    queue = []
if queue is None:
    queue = []
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
