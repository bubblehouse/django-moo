# pylint: disable=no-value-for-parameter,unused-variable
"""
Tests for dynamic room lighting via the is_lit verb and the alight property.

Covers:
  - is_lit() return values under various setups
  - tell_contents suppression in dark unlit rooms
  - look verb blocking in dark unlit rooms
  - look at inventory item still works in dark rooms
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.sdk import create, lookup
from .utils import setup_room


def _make_thing(name, room, obvious=True, owner=None):
    system = lookup(1)
    obj = create(name, parents=[system.thing], location=room, obvious=obvious, owner=owner)
    return obj


def _make_container(name, room, owner=None):
    containers = lookup("Generic Container")
    box = create(name, parents=[containers], location=room, owner=owner)
    return box


def _set_dark(room):
    room.set_property("dark", True)


# ---------------------------------------------------------------------------
# is_lit()
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lit_when_not_dark(t_init: Object, t_wizard: Object):
    """Room with dark=False is always lit."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        assert room.is_lit() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_no_light(t_init: Object, t_wizard: Object):
    """Dark room with no alight objects is not lit."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        assert room.is_lit() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_direct_alight(t_init: Object, t_wizard: Object):
    """Dark room lit by a visible alight object."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        lantern = _make_thing("lantern", room, owner=t_wizard)
        lantern.set_property("alight", True)
        assert room.is_lit() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_alight_under_rug(t_init: Object, t_wizard: Object):
    """alight object hidden under rug does not light the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        rug = _make_thing("rug", room, owner=t_wizard)
        lantern = _make_thing("lantern", room, owner=t_wizard)
        lantern.set_property("alight", True)
        lantern.set_placement("under", rug)
        assert room.is_lit() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_alight_transparent_container(t_init: Object, t_wizard: Object):
    """alight object in a transparent (opaque=0) container lights the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        box = _make_container("glass box", room, owner=t_wizard)
        box.set_property("opaque", 0)
        lantern = _make_thing("lantern", box, owner=t_wizard)
        lantern.set_property("alight", True)
        assert room.is_lit() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_alight_blackhole_container(t_init: Object, t_wizard: Object):
    """alight object in a black-hole (opaque=2) container does not light the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        box = _make_container("iron box", room, owner=t_wizard)
        box.set_property("opaque", 2)
        lantern = _make_thing("lantern", box, owner=t_wizard)
        lantern.set_property("alight", True)
        assert room.is_lit() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_alight_opaque_container_closed(t_init: Object, t_wizard: Object):
    """alight object in a closed opaque (opaque=1) container does not light the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        box = _make_container("wooden box", room, owner=t_wizard)
        box.set_property("opaque", 1)
        # open defaults to False
        lantern = _make_thing("lantern", box, owner=t_wizard)
        lantern.set_property("alight", True)
        assert room.is_lit() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dark_alight_opaque_container_open(t_init: Object, t_wizard: Object):
    """alight object in an open opaque (opaque=1) container lights the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        _set_dark(room)
        box = _make_container("wooden box", room, owner=t_wizard)
        box.set_property("opaque", 1)
        box.set_property("open", True)
        lantern = _make_thing("lantern", box, owner=t_wizard)
        lantern.set_property("alight", True)
        assert room.is_lit() is True


# ---------------------------------------------------------------------------
# tell_contents / look
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_suppressed_when_dark(t_init: Object, t_wizard: Object):
    """In a dark unlit room, obvious objects are not listed."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        _set_dark(room)
        _make_thing("golden idol", room, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "look")
    assert not any("golden idol" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_shown_when_lit(t_init: Object, t_wizard: Object):
    """Dark room with a visible alight object shows other obvious objects."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        _set_dark(room)
        lantern = _make_thing("lantern", room, owner=t_wizard)
        lantern.set_property("alight", True)
        _make_thing("golden idol", room, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "look")
    assert any("golden idol" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_at_room_object_blocked_in_dark(t_init: Object, t_wizard: Object):
    """'look at X' for a room object is blocked when dark and unlit."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        _set_dark(room)
        _make_thing("ancient desk", room, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "look at ancient desk")
    assert any("dark" in line.lower() for line in printed)
    assert not any("ancient desk" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_at_inventory_item_works_in_dark(t_init: Object, t_wizard: Object):
    """'look at X' for an inventory item succeeds even when the room is dark."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        _set_dark(room)
        torch = _make_thing("old torch", t_wizard, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "look at old torch")
    assert not any("dark" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_under_blocked_in_dark(t_init: Object, t_wizard: Object):
    """'look under X' is blocked when the room is dark and unlit."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        _set_dark(room)
        rug = _make_thing("dusty rug", room, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "look under dusty rug")
    assert any("dark" in line.lower() for line in printed)
