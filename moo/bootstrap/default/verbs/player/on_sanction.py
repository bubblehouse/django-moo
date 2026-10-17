#!moo verb on_sanction --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Called on an avatar after staff suspend, ban, or mute its account, with the kind
(``"suspend"``, ``"ban"``, or ``"mute"``) in `args[0]`. The default does
nothing; a game overrides it to react, for example to end a role the player
holds.
"""

pass  # pylint: disable=unnecessary-pass
