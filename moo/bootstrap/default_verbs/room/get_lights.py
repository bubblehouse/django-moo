#!moo verb get_lights --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Return the list of objects currently providing light in this room.

An object contributes light if it has ``alight=True`` and is actually visible.
Includes objects directly in the room and light sources inside transparent
containers (or open ``opaque=1`` containers). Excludes objects with hidden
placement (under/behind) and anything sealed in a closed opaque container.
"""

from moo.sdk import NoSuchPropertyError, prefetch_property

lights = []

all_items = list(this.contents.select_related("placement_target").all())
visible = [item for item in all_items if not item.is_hidden_placement()]

if not visible:
    return lights

prefetch_property(visible, "alight")
prefetch_property(visible, "opaque")
prefetch_property(visible, "open")

for item in visible:
    try:
        if item.get_property("alight"):
            lights.append(item)
    except NoSuchPropertyError:
        pass

    try:
        opaque = item.get_property("opaque")
    except NoSuchPropertyError:
        continue

    if opaque == 2:
        continue
    if opaque == 1:
        try:
            is_open = item.get_property("open")
        except NoSuchPropertyError:
            is_open = False
        if not is_open:
            continue

    sub_items = list(item.contents.all())
    if sub_items:
        prefetch_property(sub_items, "alight")
        for sub in sub_items:
            try:
                if sub.get_property("alight"):
                    lights.append(sub)
            except NoSuchPropertyError:
                pass

return lights
