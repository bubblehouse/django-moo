#!moo verb set_opaque --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
Called by ``@opacity``. It sets the property opaque to be either 0, 1 or 2.
"""

from moo.sdk import require_caller_perms

require_caller_perms("write", this)

opaque = args[0]

this.set_property("opaque", opaque)
