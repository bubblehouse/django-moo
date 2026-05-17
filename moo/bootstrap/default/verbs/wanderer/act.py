#!moo verb act --on $wanderer

# pylint: disable=return-outside-function,undefined-variable

"""
Pick a random room from ``this.wander_rooms`` (a list of Object PKs), drop
the current location from the candidates, and teleport there. The room the
NPC leaves sees ``wander_leave_msg``; the room they arrive in sees
``wander_arrive_msg``. Both messages run through ``pronoun_sub`` with
``%N`` = the NPC's name.

A no-op if ``wander_rooms`` is empty, missing, or only contains the current
location. Bad PKs (deleted rooms) are silently skipped.
"""

import random

from moo.sdk import lookup, NoSuchObjectError, NoSuchPropertyError

try:
    room_pks = this.get_property("wander_rooms") or []
except NoSuchPropertyError:
    return

current_pk = this.location.pk if this.location else None
candidates = [pk for pk in room_pks if pk != current_pk]
if not candidates:
    return

try:
    dest = lookup(random.choice(candidates))
except NoSuchObjectError:
    return

old_room = this.location
leave_tmpl = this.get_property("wander_leave_msg") or "%N wanders off."
arrive_tmpl = this.get_property("wander_arrive_msg") or "%N wanders in."
leave_msg = _.string_utils.pronoun_sub(leave_tmpl, this)
arrive_msg = _.string_utils.pronoun_sub(arrive_tmpl, this)

if old_room is not None:
    old_room.announce_all_but(this, leave_msg)
this.moveto(dest)
dest.announce_all_but(this, arrive_msg)
