#!moo verb open --on $container --dspec this

# pylint: disable=return-outside-function,undefined-variable

"""
This verb will open the container and allow objects to be put into it (via the put verb).
This verb sets the property `opened` to `True`.
"""

from moo.core import api

if this.is_open():
    print("Container is already open.")
elif this.is_openable_by(api.player):
    this.set_opened(True)
    print("You open the container.")
