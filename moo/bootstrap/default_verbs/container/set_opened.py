#!moo verb set_opened --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
Called by open and close, with the arguments `True` and `False` respectively. The property `opened` is set
to either `True` (opened) or `False` (closed).
"""

is_open_flag = bool(args[0])

this.set_property("open", is_open_flag)
