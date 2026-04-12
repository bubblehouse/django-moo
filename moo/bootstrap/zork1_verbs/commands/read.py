#!moo verb read --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Read a readable object (book, sign, etc.)."""

from moo.sdk import context, NoSuchObjectError, NoSuchPropertyError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't see that here.")
    return

if not _.zork_sdk.flag(obj, "readable"):
    print(f"There's nothing to read on the {_.zork_sdk.desc(obj)}.")
    return

try:
    text = obj.get_property("text")
    print(text)
except NoSuchPropertyError:
    try:
        print(obj.get_property("description"))
    except NoSuchPropertyError:
        print(f"There's nothing written on the {_.zork_sdk.desc(obj)}.")
