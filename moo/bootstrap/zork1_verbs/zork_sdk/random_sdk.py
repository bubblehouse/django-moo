#!moo verb pick --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Pick a random element from a ZIL table stored on $zork_sdk.

args[0] = table name in UPPER-KEBAB-CASE (e.g. "HERO-MELEE")
Table is stored as property "zstate_hero_melee" on this ($zork_sdk).
"""

import random

key = "zstate_" + args[0].lower().replace("-", "_")
table = this.get_property(key)
return random.choice(table)
