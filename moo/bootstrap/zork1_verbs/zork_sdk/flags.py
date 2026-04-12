#!moo verb flag set_flag --on $zork_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Read or write a boolean flag property on a Zork object.

flag:     args[0] = object, args[1] = property name
          Returns bool (False if property missing)
set_flag: args[0] = object, args[1] = property name, args[2] = value
"""

from moo.sdk import NoSuchPropertyError

if verb_name == "set_flag":
    args[0].set_property(args[1], bool(args[2]))
else:
    try:
        return bool(args[0].get_property(args[1]))
    except NoSuchPropertyError:
        return False
