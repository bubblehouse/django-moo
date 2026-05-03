#!moo verb pick --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Pick a random element from a ZIL table stored on $zil_sdk.

args[0] = table name in UPPER-KEBAB-CASE (e.g. "HERO-MELEE")
Table is stored as property "zstate_hero_melee" on this ($zil_sdk).
"""

import random
import re

raw = args[0]
safe = re.sub(r"[^a-z0-9_]", "_", raw.lower().replace("-", "_"))
if not safe:
    raise ValueError(f"zstate table name cannot be empty (got {raw!r})")
key = "zstate_" + safe
table = this.get_property(key)
return random.choice(table)
