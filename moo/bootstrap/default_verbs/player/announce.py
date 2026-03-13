#!moo verb announce announce_all_but --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Call the `announce` and `announce_all_but`` verbs in the player``s location, if those verbs are
defined, and the player is in a valid location. It is used by noisy objects in player's inventories that wish to
broadcast messages to both the player, and others in the surrounding room.
"""

from moo.core import context

location = context.player.location
if location and location.has_verb(verb_name):
    location.invoke_verb(verb_name, *args, **kwargs)
