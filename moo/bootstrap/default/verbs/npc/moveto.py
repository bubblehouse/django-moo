#!moo verb moveto --on $npc

# pylint: disable=return-outside-function,undefined-variable

"""
Resolve the ``moveto`` ambiguity that ``$npc``'s multi-parent inheritance
creates: both ``$thing.moveto`` (via ``$daemon``) and ``$root_class.moveto``
(via ``$player``) reach an ``$npc`` descendant at the same depth and weight,
so an inherited lookup fails with ``AmbiguousVerbError``.

Inlines the ``$thing.moveto`` contract — clear any placements pointing into
the current room, then honour the destination's lock — and the
``$root_class.moveto`` set-location step. Bypassing ``passthrough()`` is
intentional; that walk would hit the same ambiguity.
"""

from moo.sdk import set_task_perms

where = args[0]

if this.location:
    for placed in list(this.placed_objects.filter(location=this.location).all()):
        placed.clear_placement()

if not where.is_unlocked_for(this):
    return False

with set_task_perms(this.owner):
    this.location = where
    this.save()
return True
