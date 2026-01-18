#!moo verb huh2 --on $room

"""
This verb is called by the `huh` verb to provide default handling of unrecognized commands given to players
in this room. You can override this verb to provide custom handling of such commands. If you wish to
fall back to the default behavior, you can use `passthrough()` to call the parent room's `huh2` verb.
"""

from moo.core import api

api.caller.tell("Huh? I don't understand that command.")
