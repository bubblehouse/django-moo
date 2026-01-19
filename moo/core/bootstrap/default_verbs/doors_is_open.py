#!moo verb is_open is_locked --on "Generic Exit" --dspec this

door = this  # pylint: disable=undefined-variable. # type: ignore

if verb_name == "is_open":  # pylint: disable=undefined-variable. # type: ignore
    prop_name = "open"
elif verb_name == "is_locked":  # pylint: disable=undefined-variable. # type: ignore
    prop_name = "locked"
else:
    print("Unknown verb name for door state check: %s" % verb_name)  # pylint: disable=undefined-variable. # type: ignore
    return False  # pylint: disable=return-outside-function  # type: ignore

if door.has_property(prop_name) and door.get_property(prop_name):
    return True  # pylint: disable=return-outside-function  # type: ignore
else:
    return False  # pylint: disable=return-outside-function  # type: ignore
