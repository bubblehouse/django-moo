#!moo verb burn --on $letter --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Recycle the letter after it has been read by the recipient, completely removing it from the database.

This verb first checks to see if the letter is readable by the person who is attempting to burn it. If it is, the
letter will be completely destroyed. If it is not readable, the command will fail.
"""

from moo.core import context

name = this.title()
if this.is_readable_by(context.player):
    context.player.tell(f"{name} burns with a smokeless flame, and leaves no ash.")
    context.player.location.announce(f"{context.player.name} stares at {name} and it catches alight.")
    this.delete()
else:
    context.player.tell(f"{name} might be damp, in any case it won't burn.")
