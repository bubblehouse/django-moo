#!moo verb @who --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
List all currently connected players and their locations.

Usage:
    @who

Displays each connected player's name and current location using
their ``who_location_msg`` verb.
"""

from moo.sdk import connected_players

players = connected_players()
if not players:
    print("No players are currently connected.")
    return

print("Connected players:")
for player in players:
    print(f"  {player.who_location_msg()}")
