#!moo verb open close shut --on $player --dspec any
# pylint: disable=return-outside-function,undefined-variable
"""Open or close a door, container, or object."""

from moo.sdk import context, NoSuchObjectError

try:
    obj = context.parser.get_dobj()
except NoSuchObjectError:
    print("You don't see that here.")
    return

if not _.zork_sdk.flag(obj, "is_door") and not obj.has_verb("open_action"):
    # Try it as a container
    pass

if verb_name == "open":
    if _.zork_sdk.flag(obj, "open"):
        print(f"The {_.zork_sdk.desc(obj)} is already open.")
        return
    _.zork_sdk.set_flag(obj, "open", True)
    print("Opened.")
    if obj.has_verb("open_action"):
        obj.invoke_verb("open_action")
else:
    if not _.zork_sdk.flag(obj, "open"):
        print(f"The {_.zork_sdk.desc(obj)} is already closed.")
        return
    _.zork_sdk.set_flag(obj, "open", False)
    print("Closed.")
    if obj.has_verb("close_action"):
        obj.invoke_verb("close_action")
