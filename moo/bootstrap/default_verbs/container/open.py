#!moo verb open --on $container --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
Open the container and allow objects to be put into it.

This verb sets the property `opened` to `True`.
"""

from moo.sdk import context

if this.is_open():
    print("Container is already open.")
elif this.is_openable_by(context.player):
    this.set_opened(True)
    print("You open the container.")
