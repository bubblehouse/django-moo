#!moo verb is_lit --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Returns True if the room has enough light to see.

A dark room (dark=True) is considered lit if at least one object with alight=True
is visibly present — not hidden under or behind something, and not sealed inside
an opaque container.

Opacity rules for containers:
  opaque=False/0 (default) — transparent; light always shines through
  opaque=1                 — light shines through only when container is open
  opaque=2                 — black hole; light never escapes
"""

from moo.sdk import NoSuchPropertyError, prefetch_property

if not this.get_property("dark"):
    return True

all_items = list(this.contents.select_related("placement_target").all())
visible = [item for item in all_items if not item.is_hidden_placement()]

if not visible:
    return False

prefetch_property(visible, "alight")
prefetch_property(visible, "opaque")
prefetch_property(visible, "open")

for item in visible:
    try:
        if item.get_property("alight"):
            return True
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
                    return True
            except NoSuchPropertyError:
                pass

return False
