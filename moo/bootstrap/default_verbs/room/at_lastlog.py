#!moo verb @lastlog lastlog --on $room --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
List the times that players last connected to the MOO. If `player` is supplied, by
invoking the verb as a command, only the last connect time for that player is shown.

If no argument is supplied, the verb uses the players() primitive to return a list of all players in the database. It
then looks at each player's `last_connected_time` property, and places them in a particular list, depending on whether
the player connected within the last day, week, month, or longer.

When all players have been placed in one or other of the lists, they are printed out, along with the exact connect time
as found in the player's `last_connected_time` property.
"""

from datetime import datetime, timedelta, timezone

from moo.core import context, players, NoSuchPropertyError

player = context.player
parser = context.parser
now = datetime.now(timezone.utc)

if parser.has_dobj_str():
    if parser.has_dobj():
        obj = parser.get_dobj()
    else:
        obj = parser.get_dobj(lookup=True)
    try:
        last_time = obj.get_property("last_connected_time")
    except NoSuchPropertyError:
        last_time = None
    if last_time is None:
        print(f"{obj.name}: has never connected.")
    else:
        print(f"{obj.name}: last connected {last_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
else:
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(weeks=1)
    month_ago = now - timedelta(days=30)

    today, this_week, this_month, older = [], [], [], []

    for avatar in players():
        try:
            last_time = avatar.get_property("last_connected_time")
        except NoSuchPropertyError:
            last_time = None

        if last_time is None:
            older.append((avatar, last_time))
        elif last_time >= day_ago:
            today.append((avatar, last_time))
        elif last_time >= week_ago:
            this_week.append((avatar, last_time))
        elif last_time >= month_ago:
            this_month.append((avatar, last_time))
        else:
            older.append((avatar, last_time))

    def print_group(label, group):
        if group:
            print(f"[bold]{label}[/bold]")
            for avatar, last_time in group:
                if last_time:
                    print(f"  {avatar.name}: {last_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                else:
                    print(f"  {avatar.name}: never connected")

    print_group("Connected within the last day:", today)
    print_group("Connected within the last week:", this_week)
    print_group("Connected within the last month:", this_month)
    print_group("Connected more than a month ago (or never):", older)
