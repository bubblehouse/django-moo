"""Tests for the escape guarantee + connectivity guard (spec 200, item M)."""

import pytest

from .. import code, create
from ..models import Object
from ...sdk import lookup, guaranteed_moveto, send_home, check_room_connectivity


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_guaranteed_moveto_bypasses_accept(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        trap = create("Trap Room", parents=[lookup("Generic Room")])
        trap.add_verb("accept", code="return False", direct_object="any", replace=True)
        mover = create("mover", parents=[lookup("Generic Thing")])
        # A normal move into the trap is refused.
        mover.location = trap
        with pytest.raises(PermissionError):
            mover.save()
        mover.refresh_from_db()
        # The guaranteed move bypasses accept.
        guaranteed_moveto(mover, trap)
        mover.refresh_from_db()
        assert mover.location == trap


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_send_home_escapes_a_trap(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        trap = create("Black Hole", parents=[lookup("Generic Room")])
        guaranteed_moveto(t_wizard, trap)
        assert t_wizard.location == trap
        dest = send_home(t_wizard)
        t_wizard.refresh_from_db()
        assert t_wizard.location == dest
        assert t_wizard.location != trap


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_connectivity_flags_dead_end(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        room = create("Dead End", parents=[lookup("Generic Room")])
        room.set_property("exits", [])
        report = check_room_connectivity(room)
        assert report["has_exit"] is False
        assert report["issues"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_connectivity_flags_one_way_exit(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        a = create("Room A", parents=[lookup("Generic Room")])
        b = create("Room B", parents=[lookup("Generic Room")])
        a.set_property("exits", [])
        b.set_property("exits", [])
        east = create("east", parents=[lookup("Generic Exit")])
        east.set_property("source", a)
        east.set_property("dest", b)
        a.set_property("exits", [east])
        report = check_room_connectivity(a)
        assert "east" in report["one_way_exits"]
        assert report["issues"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_connectivity_ok_for_two_way(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        a = create("Hall A", parents=[lookup("Generic Room")])
        b = create("Hall B", parents=[lookup("Generic Room")])
        east = create("east", parents=[lookup("Generic Exit")])
        east.set_property("source", a)
        east.set_property("dest", b)
        west = create("west", parents=[lookup("Generic Exit")])
        west.set_property("source", b)
        west.set_property("dest", a)
        a.set_property("exits", [east])
        b.set_property("exits", [west])
        report = check_room_connectivity(a)
        assert report["issues"] == []
