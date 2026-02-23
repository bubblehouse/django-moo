#!moo verb close --on $container --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
This is the opposite of open. If the pipe is already close, an error message is printed.
"""

from moo.core import api

if not this.opened:
    print("Container is already closed.")
elif this.is_openable_by(api.player):
    this.set_opened(False)
    print("You close the container.")
