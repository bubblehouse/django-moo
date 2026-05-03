#!moo verb flag set_flag getp --on $zil_sdk
# pylint: disable=return-outside-function,undefined-variable
"""
Read or write properties on a Zork object.

flag:     args[0] = object, args[1] = property name
          Returns bool (False if property missing)
set_flag: args[0] = object, args[1] = property name, args[2] = value
getp:     args[0] = object, args[1] = property name [, args[2] = default]
          Returns the property value, or default (None) if not defined.
          ZIL's ``<GETP obj prop>`` returns 0 for missing properties; verb
          translation routes through this helper to avoid NoSuchPropertyError.
"""

from moo.sdk import NoSuchPropertyError

if verb_name == "set_flag":
    args[0].set_property(args[1], bool(args[2]))
elif verb_name == "getp":
    obj = args[0]
    name = args[1]
    default = args[2] if len(args) > 2 else None
    if obj is None:
        return default
    try:
        return obj.get_property(name)
    except NoSuchPropertyError:
        return default
else:
    try:
        return bool(args[0].get_property(args[1]))
    except NoSuchPropertyError:
        return False
