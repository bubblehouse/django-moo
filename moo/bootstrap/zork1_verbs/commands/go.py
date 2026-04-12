#!moo verb go walk run --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Move in a direction (e.g. go north, go east)."""

from moo.sdk import context, NoSuchObjectError

try:
    direction = context.parser.get_dobj_str()
except NoSuchObjectError:
    print("Go where?")
    return

_.zork_sdk.walk(direction)
