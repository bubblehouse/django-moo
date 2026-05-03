#!moo verb run_v_routine --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""ZIL ACTION → V-routine fall-through.

ZIL semantics: an object's ACTION routine runs first.  If it returns FALSE
(no print, no early return), the standard ``V-<verb>`` runs.  In Python the
per-object routine just falls off the end without an explicit ``return``;
this helper picks up where it left off and invokes the matching ``V-*``
verb on ``$zork_thing``.

Args:
    args[0] = verb_name (the player verb the action was dispatched for)
    args[1] = optional dobj override (defaults to context.parser.get_dobj())
"""

from moo.sdk import context, NoSuchObjectError

verb_name_arg = args[0] if args else None
if not verb_name_arg:
    return

# Map player verb → V-routine name.  Most are ``v-<verb>``; a handful of
# ZIL idioms (lamp-on / lamp-off / look-under) follow the same pattern with
# their hyphenated names.
v_name = "v-" + verb_name_arg

zork_thing = _.get_property("zork_thing")
if zork_thing is None or not zork_thing.has_verb(v_name):
    # No standard V-routine for this verb; nothing to fall through to.
    return

# Set context.parser dobj if a manual override was passed (some action
# routines call this with an explicit object).
zork_thing.invoke_verb(v_name)
