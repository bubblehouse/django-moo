#!moo verb emote --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Handle the pose type of interaction with other players. It functions in a similar way to the :say verb,
but places the player's name at the front of the text: `emote waves` shows everyone "Phil waves". Because the line
always starts with the actor's name, an emote cannot make another player appear to act. The output is done in two
stages. The :emote verb tells the player the line; the emote1 verb then tells the other objects in the room. Either or
both of the verbs can be overridden to provide special effects. A muted player's emote reaches no one.
"""

from moo.sdk import account_for, connected_players, context, is_muted, send_gmcp

if is_muted(account_for(context.player)):
    context.player.tell("You are muted.")
    return

if context.parser.words:
    message = " ".join(context.parser.words[1:])
else:
    message = " ".join(args)

line = context.player.name + " " + message
context.player.tell(line)
this.emote1(line)

gmcp_event = {"channel": "emote", "talker": context.player.name, "text": message}
connected = {p.pk for p in connected_players()}
for obj in this.contents.all():
    if obj.pk in connected:
        send_gmcp(obj, "Comm.Channel.Text", gmcp_event)
