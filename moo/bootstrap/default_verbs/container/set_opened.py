#!moo verb set_opened --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is called by open and close, with the arguments `True` and `False` respectively. The property `opened` is set
to either `True` (opened) or `False` (closed).
"""

opened = args[0]

this.set_property("opened", opened)
