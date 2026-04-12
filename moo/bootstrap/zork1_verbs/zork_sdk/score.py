#!moo verb score_update --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Add points to the player's Zork score.

args[0] = integer delta (positive for points gained)
Score is stored per-player as "zstate_score".
"""

from moo.sdk import context, NoSuchPropertyError

try:
    score = context.player.get_property("zstate_score")
except NoSuchPropertyError:
    score = 0
context.player.set_property("zstate_score", score + args[0])
