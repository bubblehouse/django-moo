#!moo verb is_open is_locked --on $exit --dspec this

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

from moo.sdk import NoSuchPropertyError

door = this

if verb_name == "is_open":
    try:
        return bool(door.get_property("open"))
    except NoSuchPropertyError:
        return False
elif verb_name == "is_locked":
    try:
        return bool(door.get_property("key"))
    except NoSuchPropertyError:
        return False
else:
    print("Unknown verb name for door state check: %s" % verb_name)
    return False
