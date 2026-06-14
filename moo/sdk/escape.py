# -*- coding: utf-8 -*-
"""
Escape guarantee and connectivity guard (spec 200, item M).

Programmer-built interiors can become black holes — one-way exits, no way back,
``accept`` verbs that refuse everyone.  :func:`guaranteed_moveto` is the engine
guarantee that ``home`` always works regardless of the room owner's verbs/locks;
:func:`check_room_connectivity` is the build-time guard that catches a room a
player could get stuck in.
"""

from .context import context


def guaranteed_moveto(obj, dest):
    """Move ``obj`` to ``dest``, bypassing the destination's ``accept``/locks.

    The un-trappable panic move (used by ``home``): even a misconfigured or
    hostile destination cannot refuse it.  ``enterfunc``/``exitfunc`` still run.

    :param obj: the Object to move (typically a player)
    :param dest: the destination Object
    :return: the moved Object
    """
    obj._guaranteed_move = True  # pylint: disable=protected-access
    try:
        obj.location = dest
        obj.save()
    finally:
        obj._guaranteed_move = False  # pylint: disable=protected-access
    return obj


def send_home(player):
    """Send a player home, guaranteed.

    Tries the player's ``home`` (or ``$player_start`` if unset) and forces the
    move so it cannot be blocked.  This is the engine-level escape the ``home``
    verb delegates to.

    :param player: the player Object
    :return: the destination the player landed in
    """
    from ..core.exceptions import NoSuchPropertyError
    from ..core.models import Object

    home = None
    try:
        home = player.get_property("home")
    except NoSuchPropertyError:
        home = None
    if not home:
        system = Object.objects.get(unique_name=True, name="System Object")
        home = system.get_property("player_start")
    guaranteed_moveto(player, home)
    return home


def check_room_connectivity(room):
    """Report whether a room is a potential trap (spec 200, item M).

    A build-completion guard: flags a room with no way out, and any exit whose
    destination has no exit leading back (a one-way trip).

    :param room: the room Object to check
    :return: ``{"has_exit": bool, "one_way_exits": [names], "issues": [str]}``
    """
    from ..core.exceptions import NoSuchPropertyError

    def _dest(exit_obj):
        try:
            return exit_obj.get_property("dest")
        except NoSuchPropertyError:
            return None

    issues = []
    exits = room.get_property_objects("exits") or []
    has_exit = len(exits) > 0
    if not has_exit:
        issues.append("Room has no exits — anyone here is stuck (only `home` escapes).")

    one_way = []
    for exit_obj in exits:
        dest = _dest(exit_obj)
        if dest is None:
            continue
        back = dest.get_property_objects("exits") or []
        if not any(_dest(b) == room for b in back):
            label = exit_obj.name or "exit"
            one_way.append(label)
            issues.append(f"Exit '{label}' to {dest.name} has no exit back.")

    return {"has_exit": has_exit, "one_way_exits": one_way, "issues": issues}
