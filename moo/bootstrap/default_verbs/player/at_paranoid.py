#!moo verb @par*anoid --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Set the player's paranoid level, as stored in the `paranoid` property. Three different levels are
available:

``0``
    The normal case, where no paranoia is applied to any messages sent to the player.
``1``
    In this case, the anti-spoofer is enabled, and the value of the ``lines`` property on the player is set to 20.
    This determines how many messages are stored on the player, for checking with the ``@check`` command.
``2``
    In this case, every message sent to the player is prefixed with the name and object number of the sender. This
    is the immediate mode of the anti-spoofer mechanism.
"""

from moo.core import context

level = context.parser.get_dobj_str()
if level not in ("0", "1", "2"):
    print("Paranoid level must be 0, 1, or 2.")
else:
    context.player.paranoid = int(level)
