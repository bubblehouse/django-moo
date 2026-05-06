#!moo verb pick --on "System Object"
# pylint: disable=return-outside-function,undefined-variable
"""
Pick a random element from a ZIL table.

args[0] = either:
    - a table list (the value of a ZIL global, e.g. ``zstate_get("YUKS")``), or
    - a table name in UPPER-KEBAB-CASE (e.g. "HERO-MELEE"), looked up on
      ``this`` (the System Object) as ``zstate_<lower_snake>``.

ZIL tables typically have a leading length-marker (0) or "PURE" sentinel;
those are skipped so callers do not see them as a return value.
"""

import random
import re

raw = args[0]
if isinstance(raw, list):
    table = raw
elif raw is None:
    return None
else:
    safe = re.sub(r"[^a-z0-9_]", "_", raw.lower().replace("-", "_"))
    if not safe:
        raise ValueError(f"zstate table name cannot be empty (got {raw!r})")
    key = "zstate_" + safe
    table = this.get_property(key)
choices = [x for x in table if x != 0 and x != "PURE"]
if not choices:
    return None
return random.choice(choices)
