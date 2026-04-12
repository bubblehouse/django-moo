#!moo verb inventory i inv --on $player
# pylint: disable=return-outside-function,undefined-variable
"""List the player's inventory."""

from moo.sdk import context

items = list(context.player.contents.all())
if not items:
    print("You are empty-handed.")
    return

print("You are carrying:")
for item in items:
    print(f"  {_.zork_sdk.desc(item)}")
