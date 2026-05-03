#!moo verb zstate_get zstate_set table_get table_put --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
ZIL state primitives.

zstate_get: args[0] = key in UPPER-KEBAB-CASE (e.g. "CYCLOPS-FLAG")
zstate_set: args[0] = key, args[1] = value
table_get:  args[0] = list, args[1] = index → list[index] (or None)
table_put:  args[0] = list, args[1] = index, args[2] = value (in-place)

zstate_* persists per-player so multiple players have independent game
state.  table_* are pure list operations on the value passed in — ZIL's
``<GET TABLE I>`` / ``<PUT TABLE I VAL>`` primitives.
"""

import re

from moo.sdk import context, NoSuchPropertyError

if verb_name == "table_get":
    table = args[0] if args else None
    idx = args[1] if len(args) > 1 else 0
    if table is None or not isinstance(table, list):
        return None
    if idx is None or idx < 0 or idx >= len(table):
        return None
    return table[idx]

if verb_name == "table_put":
    table = args[0] if args else None
    idx = args[1] if len(args) > 1 else 0
    val = args[2] if len(args) > 2 else None
    if table is None or not isinstance(table, list):
        return None
    if idx is None or idx < 0:
        return None
    while len(table) <= idx:
        table.append(0)
    table[idx] = val
    return val

# zstate_get / zstate_set fall through to the per-player storage path.
raw_key = args[0]
sanitized = re.sub(r"[^a-z0-9_]", "_", raw_key.lower().replace("-", "_"))
if not sanitized:
    raise ValueError(f"zstate key cannot be empty (got {raw_key!r})")
key = "zstate_" + sanitized
if verb_name == "zstate_set":
    context.player.set_property(key, args[1])
else:
    try:
        return context.player.get_property(key)
    except NoSuchPropertyError:
        return None
