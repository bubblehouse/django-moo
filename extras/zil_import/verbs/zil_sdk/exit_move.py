#!moo verb move --on "Zork Exit"
# pylint: disable=return-outside-function,undefined-variable

"""
Zork-specific exit traversal.  Replaces the bulk of the legacy ``walk``
dispatcher in ``movement.py`` so per-exit overrides for conditional,
per-routine, and door variants can live as ``move`` verbs on individual
exit Objects rather than data branches in one giant function.

The contract mirrors the native ``$exit.move``: ``args[0]`` is the entity
being moved.  For Zork that's almost always the player or a vehicle the
player is inside; the boat case is handled by ``current_vehicle`` so the
entire vehicle relocates and the player's ``location`` stays the boat.

Property contract on the exit Object:

    source        — origin room
    dest          — destination room (None means routine-driven or blocked)
    nogo_msg      — printed when dest is missing or condition fails
    message       — printed on successful traversal
    exit_routine  — name of a ``$zork_thing`` verb whose return value is
                    the destination room (None → blocked).  The routine
                    prints its own block message.
"""

from moo.sdk import context, NoSuchPropertyError


def current_vehicle():
    loc = context.player.location
    if loc is None:
        return None
    try:
        is_veh = loc.get_property("vehicle")
    except NoSuchPropertyError:
        is_veh = False
    return loc if is_veh else None


def resolve_dest():
    try:
        dest = this.get_property("dest")
    except NoSuchPropertyError:
        dest = None
    if dest is not None:
        return dest
    # exit_routine is a verb name on $zork_thing returning the
    # destination room (or None to block).  The routine prints its
    # own block message before returning None.
    try:
        routine_name = this.get_property("exit_routine")
    except NoSuchPropertyError:
        return None
    if not routine_name:
        return None
    # ZIL routine atoms are UPPER-KEBAB (e.g. ``TRAP-DOOR-EXIT``); the
    # generator registers them as snake_case verbs (``trap_door_exit``)
    # so dot-syntax dispatch works.  Snake-case the lookup name.
    verb_name_snake = routine_name.lower().replace("-", "_")
    zthing = _.get_property("zork_thing")
    if zthing is None or not zthing.has_verb(verb_name_snake):
        return None
    return zthing.invoke_verb(verb_name_snake)


dest = resolve_dest()
if not dest:
    try:
        print(this.get_property("nogo_msg"))
    except NoSuchPropertyError:
        try:
            this.get_property("exit_routine")  # routine printed its own message
        except NoSuchPropertyError:
            print("You can't go that way.")
    return

try:
    print(this.get_property("message"))
except NoSuchPropertyError:
    pass

veh = current_vehicle()
if veh is not None:
    veh.location = dest
    veh.save()
else:
    context.player.location = dest
    context.player.save()

if dest.has_verb("look_action"):
    dest.invoke_verb("look_action")
elif dest.has_verb("look"):
    dest.invoke_verb("look")
else:
    try:
        print(dest.get_property("description"))
    except NoSuchPropertyError:
        print(f"You enter {dest.name}.")
