#!moo verb score --on $player
# pylint: disable=return-outside-function,undefined-variable
"""Display the player's current score and move count."""

from moo.sdk import context, NoSuchPropertyError

try:
    score = context.player.get_property("zstate_score")
except NoSuchPropertyError:
    score = 0

try:
    moves = context.player.get_property("zstate_moves")
except NoSuchPropertyError:
    moves = 0

print(f"Your score is {score} in {moves} moves.")
