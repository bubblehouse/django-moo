#!moo verb examine x describe --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Examine an object to get its description."""

from moo.sdk import context, NoSuchObjectError, NoSuchPropertyError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't see that here.")
    return

try:
    desc = obj.get_property("description")
    print(desc)
except NoSuchPropertyError:
    print(f"There's nothing special about the {_.zork_sdk.desc(obj)}.")

if obj.has_verb("examine_action"):
    obj.invoke_verb("examine_action")
