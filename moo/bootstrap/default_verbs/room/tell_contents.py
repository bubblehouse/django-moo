#!moo verb tell_contents --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Tell the player what things are visible in the room. It goes through the contents list of the room, and if it is not
dark, prints the name of the object in a nicely formatted way. Three different formats are available depending on the
value of the `content_list_type` property of the room. These are best illustrated by example.

Consider the a room in the LambdaCore database. With a `content_list_type` value of three (the default), the
`tell_contents` verb produces the following output:

    You see a newspaper and a fruitbat zapper here.
    Wizard is here.
    On the desk: a coffee cup.

This format provides the separation of player objects from other objects, and provides the list in a way that fits in
with the idea of a virtual reality. It is easy to read, and looks natural.

If the `content_list_type` value is changed to 2, the following is printed:

    You see Wizard, a newspaper, and a fruitbat zapper here.
    On the desk: a coffee cup.

With a `content_list_type` value of 1, the following is seen:

    Wizard is here.
    You see a newspaper here.
    You see a fruitbat zapper here.
    On the desk: a coffee cup.

With a `content_list_type` of 0, the following is seen:

    Contents:
    Wizard
    a newspaper
    a fruitbat zapper
    On the desk: a coffee cup.

If a value of `content_list_type` is set that is outside of the range zero thru three, then no contents list is
printed. This can be useful if you want to handle the room contents listing as part of the description of the room.
Also, if the `dark` property of a room is set to a non-zero value, then no contents list is printed.

As usual, this verb can be overridden to provide special effects.

Placement-aware display:
- Objects placed with a visible preposition (on, before, beside, over) are grouped under their surface.
  They appear in the surface grouping only if obvious=True.
- Objects placed with a hidden preposition (under, behind) are never shown in this listing.
  Use ``look under <target>`` or ``look behind <target>`` to reveal them.
"""

import random

from moo.sdk import context

if not this.is_lit():
    return

# If the room itself is dark but currently lit, attribute the light source(s)
# so players know which object is casting it — useful when the source is
# hidden (placed under/behind something) or sealed in a transparent container.
if this.get_property("dark"):
    lights = this.get_lights()
    if lights:
        names = _.string_utils.english_list(lights)
        print(f"The room is lit by {names}.")

PREP_DISPLAY = {"before": "in front of"}

# Collect all room contents in one query with placement_target joined.
all_items = list(this.contents.select_related("placement_target").all())

# Set of PKs for objects directly in this room (validates placement targets).
room_pks = {item.pk for item in all_items}

players = []
items = []  # unplaced obvious items
surfaces = {}  # {target_pk: (target_obj, prep, [placed_items])}

for item in all_items:
    if item == context.player:
        continue
    if item.is_player():
        players.append(item)
        continue
    if item.is_hidden_placement():
        continue  # under/behind — always hidden regardless of obvious
    if item.is_placed():
        prep, target = item.placement
        if not item.obvious:
            continue  # obvious wins for visible placements
        if target is not None and target.pk in room_pks:
            key = target.pk
            if key not in surfaces:
                surfaces[key] = (target, prep, [])
            surfaces[key][2].append(item)
        else:
            # Target not in this room (or deleted) — treat as unplaced
            items.append(item)
    elif item.obvious:
        items.append(item)

ctype = this.content_list_type
if ctype == 3:
    to_be = ("is", "are")[int(len(players) > 1)]
    if items:
        print(f"You see {_.string_utils.english_list(items)} here.")
    if players:
        if len(players) == 1:
            print(f"{players[0].title()} is here.")
        else:
            print(f"{_.string_utils.english_list(players)} {to_be} here.")
elif ctype == 2:
    all_visible = players + items
    if all_visible:
        print(f"You see {_.string_utils.english_list(all_visible)} here.")
elif ctype == 1:
    for item in players:
        print(f"{item.title()} is here")
    for item in items:
        name = item.title()
        article = "an" if name[:1].lower() in "aeiou" else "a"
        print(f"You see {article} {name} here")
elif ctype == 0:
    print("Contents:")
    for item in players:
        print(item.title())
    for item in items:
        name = item.title()
        article = "an" if name[:1].lower() in "aeiou" else "a"
        print(f"{article} {name}")

# Surface groupings appended for all content_list_type values 0-3
if ctype in (0, 1, 2, 3):
    for surface_pk in sorted(surfaces, key=lambda pk: surfaces[pk][0].title()):
        surface, prep, placed_items = surfaces[surface_pk]
        disp = PREP_DISPLAY.get(prep, prep)
        tname = surface.title()
        if len(placed_items) == 1:
            s = _.string_utils.english_list(placed_items)
            line = random.choice(
                [
                    f"{disp.capitalize()} the {tname}: {s}.",
                    f"There is {s} {disp} the {tname}.",
                    f"You see {s} {disp} the {tname}.",
                ]
            )
        else:
            lst = _.string_utils.english_list(placed_items)
            line = random.choice(
                [
                    f"{disp.capitalize()} the {tname}: {lst}.",
                    f"You see {lst} {disp} the {tname}.",
                    f"{lst.capitalize()} {disp} the {tname}.",
                ]
            )
        print(line)
