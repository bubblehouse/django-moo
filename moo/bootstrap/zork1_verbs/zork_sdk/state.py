#!moo verb zstate_get zstate_set --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Read or write a ZIL global state flag on the current player.

zstate_get: args[0] = key in UPPER-KEBAB-CASE (e.g. "CYCLOPS-FLAG")
zstate_set: args[0] = key, args[1] = value

State is stored per-player so multiple players have independent game state.
Key conversion: "CYCLOPS-FLAG" -> "zstate_cyclops_flag"
"""

from moo.sdk import context, NoSuchPropertyError

key = "zstate_" + args[0].lower().replace("-", "_")
if verb_name == "zstate_set":
    context.player.set_property(key, args[1])
else:
    try:
        return context.player.get_property(key)
    except NoSuchPropertyError:
        return None
