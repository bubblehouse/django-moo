#!moo verb is_open is_locked --on $exit --dspec this

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

from moo.sdk import NoSuchPropertyError

door = this

if verb_name == "is_open":
    prop_name = "open"
elif verb_name == "is_locked":
    prop_name = "locked"
else:
    print("Unknown verb name for door state check: %s" % verb_name)
    return False

try:
    return bool(door.get_property(prop_name))
except NoSuchPropertyError:
    return False
