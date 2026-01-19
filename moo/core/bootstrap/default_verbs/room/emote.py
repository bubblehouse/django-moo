#!moo verb emote --on $room

"""
This verb is used for the pose type of interaction with other players. It functions in a similar way to the :say verb,
but instead places the player's name at the front of the text. The actual output is done in two stages. The :emote verb
is responsible for telling the player the action s/he has just performed. The emote1 verb is then called to tell the
other objects in the room of the pose action. This provides a two stage mechanism; either or both of the verbs can be
overridden to provide special effects.
"""

from moo.core import api

if api.parser.words:
    message = " ".join(api.parser.words[1:])
else:
    message = " ".join(args)

api.caller.tell("You " + message)
this.emote1(message)
