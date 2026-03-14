#!moo verb huh2 --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Called by the `huh` verb to provide default handling of unrecognized commands given to players
in this room. You can override this verb to provide custom handling of such commands. If you wish to
fall back to the default behavior, you can use `passthrough()`` to call the parent room``s `huh2` verb.

This verb is called by the huh verb to handle commands that the parser couldn't sensibly pass to another object. In the
case of a room, the verb covers a number of different possibilities. First, the sentence is checked to see if it
matches any of the exits that lead out of the room. This is done using the `match_exit` verb. If a matching exit is
found then the `invoke` verb for the exit is called, which causes it to be activated. This provides for a flexible
approach to handling exits.

If this does not produce a sensible match, then the verb is treated in one of two ways. If it starts with an ``at`` (@)
character, then we attempt to match the remainder of the verb in the sentence with a message field on the direct object.
A message field is a property whose name ends in "_msg". If a match is found, then this is treated as a field setting
command. This approach is used to avoid having to define a verb for every message field that can exist on an object.
It also allows players to add extra message fields to objects simply by ending the name of the property with "_msg".
For example, if you define a message on an object called `foobar_msg` then you can set the message with the command

@foobar <object> is <message text>

If the verb does not start with an ``at`` (@) character, then we call the `explain` verb. This tries to match the verb
with a verb defined on the player, room, direct object (if any) and indirect object (if any). If a match is found,
the syntax of the verb (ie, number and type of arguments and prepositions) is checked, and a useful message sent to the
player.

This approach is taken to provide flexibility. By not placing this sort of code within the server, the DjangoMOO
administrator has the choice of changing the way erroneous commands are handled. One application could be an
augmentation of the basic `huh` action to log failed commands in a list somewhere. This mechanism, long used in other
MUDs, can provide a builder with an idea of what other players have tried (and failed) to do in his or her areas.
"""

from moo.core import context

player = context.player
parser = context.parser

verb = args[0]

# Step 1: Check if the verb matches an exit
exit_obj = this.match_exit(verb)
if exit_obj is not None:
    if isinstance(exit_obj, list):
        player.tell(f"I don't know which '{verb}' you mean.")
    else:
        exit_obj.invoke(player)
    return

# Step 2: If verb starts with '@', try to handle it as a _msg property setter
if verb.startswith("@"):
    msg_name = verb[1:] + "_msg"
    if parser.has_dobj_str():
        if parser.has_dobj():
            obj = parser.get_dobj()
        else:
            obj = parser.get_dobj(lookup=True)
        if obj.has_property(msg_name) and parser.has_pobj_str("is"):
            value = parser.get_pobj_str("is")
            obj.set_property(msg_name, value)
            print(f"Message '{msg_name}' set.")
            return

# Step 3: Try to explain the command; if that fails, say Huh?
if not this.explain(verb):
    player.tell("Huh? I don't understand that command.")
