#!moo verb @unlock --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Unlock an object. The direct object string is matched to try and find an object
to unlock. If a match is found, the `key` property is reset to ``None``. Any errors are reported to the invoking player.
"""

from moo.sdk import context

parser = context.parser

obj = parser.get_dobj()
obj.set_property("key", None)
