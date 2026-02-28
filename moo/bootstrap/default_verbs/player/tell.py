#!moo verb tell --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb should be used to send a message to a player. The `$player.tell` filters messages in two different ways, as
shown below. Remember that the player referred to in the code is the player sending the message. `this` refers to the
player receiving the message.

The verb `$player:gag_p` returns `True` if the player sending the message is in the recipient's gag list. For this
verb, the output from any gagged player is ignored, and not printed to the recipient's terminal.

If the `paranoid` level of the recipient is `2`, this means that they wish to see who has sent them a message. The
`$player:whodunnit` verb returns the object reference of the player that sent the message. This is prepended to the
message text, which is then printed to the player.

If the `paranoid` level of the recipient is `1`, then the message and its originator are stored in the property list
`responsible` on the player. The list is kept to `player.lines` length, at most. This option is used for later
processing by the `@check` command.
"""

from moo.core import context

player = context.player
callers = context.caller_stack + [{"caller": player, "verb_name": "", "this": player}]
if not this.gag_p():
    if this.paranoid == 2:
        z = this.whodunnit(callers, [this], [])
        passthrough("(", z.name, " #", z.pk, ") ", *args)
    else:
        passthrough(*args)
        if this.paranoid == 1:
            res = this.responsible + [callers, args]
            while len(res) > this.lines:
                res.pop(0)
            this.responsible = res
        else:
            this.responsible = []
