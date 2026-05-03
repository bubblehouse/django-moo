#!moo verb @quit QUIT --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
@quit: Disconnect from the MOO server.

QUIT is a legacy disconnect command. If the current room defines a QUIT verb it
wins dispatch automatically (last-match-wins); this fallback just redirects to @quit.
"""

from moo.sdk import context, boot_player

if verb_name == "@quit":
    print(f"Goodbye, {context.player.title()}.")
    boot_player(context.player)
else:
    print("Please use @quit to disconnect from the MOO.")
