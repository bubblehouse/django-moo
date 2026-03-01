#!moo verb @unlock --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is a player command used to unlock an object. The direct object string is matched to try and find an object
to unlock. If a match is found, the `key` property is reset to `None'. Any errors are reported to the invoking player.
"""

from moo.core import context

parser = context.parser

obj = parser.get_dobj()
obj.key = None
