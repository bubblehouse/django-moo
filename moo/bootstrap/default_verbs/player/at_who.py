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

# Deduplicate by player id — a single player with multiple connections
# (e.g. one SSH session and one webssh session) should appear once.
seen = set()
print("Connected players:")
for player in players:
    if player.id in seen:
        continue
    seen.add(player.id)
    location = player.location.name if player.location else "nowhere"
    print(f"  {player.name} [{location}]")
