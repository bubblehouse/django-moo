#!moo verb tell_contents --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
This verb tells us what things are visible in the room. It goes through the contents list of the room, and if it is not
dark, prints the name of the object in a nicely formatted way. Three different formats are available depending on the
value of the `content_list_type` property of the room. These are best illustrated by example.

Consider the a room in the LambdaCore database. With a `content_list_type` value of three (the default), the
`tell_contents` verb produces the following output:

    You see a newspaper and a fruitbat zapper here.
    Wizard is here.

This format provides the separation of player objects from other objects, and provides the list in a way that fits in
with the idea of a virtual reality. It is easy to read, and looks natural.

If the `content_list_type` value is changed to 2, the following is printed:

    You see Wizard, a newspaper, and a fruitbat zapper here.

This format treats players and objects the same, and is useful if you wish to hide the fact that an object is not a
player, or vice versa.

With a `content_list_type` value of 1, the following is seen:

    Wizard is here.
    You see a newspaper here.
    You see a fruitbat zapper here.

This format provides the advantage of having each item on a separate line, although it does mean that rooms with a
large number of objects in might have excessively long contents lists.

Finally, with a `content_list_type` of 0, the following is seen:

    Contents:
    Wizard
    a newspaper
    a fruitbat zapper

This is the sort of listing obtained in traditional TinyMU* games. It benefits from clarity, but is not as natural as
any of the other forms.

If a value of `content_list_type` is set that is outside of the range zero thru three, then no contents list is
printed. This can be useful if you want to handle the room contents listing as part of the description of the room.
Also, if the `dark` property of a room is set to a non-zero value, then no contents list is printed.

As usual, this verb can be overridden to provide special effects. For example, you could apply a filter so that certain
objects do not appear in the printed contents of a room, even if they appear in the contents list. This can be use to
hide objects, for example, as part of a puzzle, or to vary how objects are seen, for example if you are looking through
water at something.
"""

items = []
players = []
for item in this.contents.all():
    if item.is_player():
        players.append(item.title())
    else:
        items.append(item.title())

ctype = this.content_list_type
if ctype == 3:
    to_be = ('is', 'are')[int(len(players) > 1)]
    if items:
        if len(items) == 1:
            print("You see {} here.".format(items[0]))
        else:
            print("You see {} and {} here.".format(", ".join(items[:-1]),  items[-1]))
    if players:
        if len(players) == 1:
            print("You see {} here.".format(players[0]))
        else:
            print("{} and {} {} here.".format(", ".join(players[:-1]),  players[-1], to_be))
elif ctype == 2:
    items = players + items
    if items:
        if len(items) == 1:
            print("You see {} here.".format(items[0]))
        else:
            print("You see {} and {} here.".format(", ".join(items[:-1]),  items[-1]))
elif ctype == 1:
    for item in players:
        print(f"{item} is here")
    for item in items:
        print(f"You see {item} here")
elif ctype == 0:
    print("Contents:")
    for item in players + items:
        print(item)
