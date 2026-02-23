#!moo verb set_opaque --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is called by `@opacity'. It sets the property opaque to be either 0, 1 or 2.
"""

from moo.core import api

opaque = args[0]

this.set_property("opened", opened)
