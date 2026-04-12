#!moo verb quit q --on $player
# pylint: disable=return-outside-function,undefined-variable
"""Quit the game."""

from moo.sdk import context, NoSuchPropertyError

try:
    score = context.player.get_property("zstate_score")
except NoSuchPropertyError:
    score = 0

try:
    moves = context.player.get_property("zstate_moves")
except NoSuchPropertyError:
    moves = 0

print(f"\nYour score was {score} in {moves} moves.")
print("Thanks for playing Zork!")
