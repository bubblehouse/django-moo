#!moo verb is_open is_locked --on "Generic Exit" --dspec this

from moo.core import api

door = api.parser.this

if args[0] == "is_open":  # pylint: disable=undefined-variable. # type: ignore
    prop_name = "open"
else:
    prop_name = "locked"

if door.has_property(prop_name) and door.get_property(prop_name):
    return True  # pylint: disable=return-outside-function  # type: ignore
else:
    return False  # pylint: disable=return-outside-function  # type: ignore
