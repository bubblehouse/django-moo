#!moo verb page --on $player --dspec any --ispec with:any

# pylint: disable=undefined-variable,return-outside-function

"""
This verb is a player command used to send messages between players who are not physically located in the same room in
the virtual world. You can imagine a page to be a worldwide form of whispering. Without an argument, a message like:

    You sense that blip is looking for you in The Venue Hallway.

is sent to the recipient of the page. If an argument is given, it is treated as a message to send to the other player.
This results in the recipient getting a message like:

    You sense that blip is looking for you in Hallway.
    He pages, "Hello - are you busy ?"

Paging is used primarily to attract the attention of a player, or to pass short messages between players in different
locations. It is not intended to be used for conversation.

If a player name has been given as an argument, the `page` verb first tries to match the first argument with a player
name, using `$string_utils:match_player`. If a match is found, then there are two possibilities. Firstly, if the player
is not connected, a pronoun substituted version of the string returned by that player's `page_absent_msg` verb is
printed to the sender, and the verb is aborted.

Otherwise, if the recipient is connected, we send him/her the string returned by the sender's `page_origin_msg` verb.
We then check to see if, optionally, `with` followed by a message is part of the argument list for the verb. If so,
then the message is extracted from the argument list and sent to the recipient, suitably pronoun substituted. The
string returned by the recipient's `page_echo_msg` verb is printed to the sending player.

An interesting piece of coding is used to stop the line containing the message from duplicating the sender's name if it
has already been sent as part of the `page_origin_msg`. For example, if "blip" page's "Ezeke", Ezeke might see the
following:

    You sense that blip is looking for you in The Venue Hallway
    He pages, "Hello"

which would be better than something like

    You sense that blip is looking for you in The Venue Hallway
    blip pages, "Hello"

The code in question is shown below:

    who.tell(player.psc if player.name in message else player.name, " pages, \"", msg, "\"")

Here, `in` is used to check if the player's name occurs in the string we sent to the recipient as `pagemsg`. If it
does, then we print the player's subjective pronoun, capitalised. If it doesn't, we print the player's name.
"""

from moo.core import context

player = context.player
who = context.parser.get_dobj()
if context.parser.has_pobj_string("with"):
    message = context.parser.get_pobj_string("with")
else:
    message = None

pagemsg = this.page_origin_msg()
who.tell(pagemsg)
if message:
    who.tell(player.psc if player.name in message else player.name, " pages, \"", message, "\"")
