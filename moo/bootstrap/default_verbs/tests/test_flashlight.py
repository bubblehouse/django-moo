# pylint: disable=no-value-for-parameter,unused-variable
"""
Tests for the $flashlight class, its switch verb, and room get_lights behavior.

Covers:
  - Generic Flashlight class exists with expected default properties
  - switch flashlight toggles alight state on and off
  - switch narrates to caller and other players in the room
  - get_lights returns all visible alight objects
  - Light source attribution in tell_contents for dark-but-lit rooms
  - alight flashlight in a player's inventory lights a dark room
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.sdk import create, lookup
from .utils import setup_room


def _make_flashlight(location, owner, name="flashlight"):
    flashlight_cls = lookup("Generic Flashlight")
    return create(name, parents=[flashlight_cls], location=location, owner=owner)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_flashlight_class_exists(t_init: Object, t_wizard: Object):
    """$flashlight is a named class and a child of $thing."""
    system = lookup(1)
    flashlight_cls = lookup("Generic Flashlight")
    assert flashlight_cls is not None
    assert flashlight_cls in system.flashlight.parents.all() or flashlight_cls == system.flashlight
    thing = lookup("Generic Thing")
    assert thing in flashlight_cls.parents.all()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_flashlight_default_unlit(t_init: Object, t_wizard: Object):
    """New flashlight instance starts with alight=False."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        torch = _make_flashlight(t_wizard, t_wizard)
        assert bool(torch.get_property("alight")) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_switch_turns_on(t_init: Object, t_wizard: Object):
    """`switch flashlight` flips alight from False to True and narrates."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        torch = _make_flashlight(t_wizard, t_wizard)
        printed.clear()
        parse.interpret(ctx, "switch flashlight")
        torch.refresh_from_db()
    assert bool(torch.get_property("alight")) is True
    assert any("switch on" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_switch_toggles_off(t_init: Object, t_wizard: Object):
    """Calling switch a second time flips alight back to False."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        torch = _make_flashlight(t_wizard, t_wizard)
        torch.set_property("alight", True)
        printed.clear()
        parse.interpret(ctx, "switch flashlight")
        torch.refresh_from_db()
    assert bool(torch.get_property("alight")) is False
    assert any("switch off" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_lights_empty_when_none_alight(t_init: Object, t_wizard: Object):
    """get_lights returns an empty list when nothing is alight."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        torch = _make_flashlight(room, t_wizard)
        assert not list(room.get_lights())


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_lights_returns_alight_object(t_init: Object, t_wizard: Object):
    """get_lights returns a visible alight object directly in the room."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        torch = _make_flashlight(room, t_wizard)
        torch.set_property("alight", True)
        lights = room.get_lights()
        assert torch in lights


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_lights_excludes_hidden_placement(t_init: Object, t_wizard: Object):
    """An alight object placed under another object is not returned."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        rug = create("rug", parents=[system.thing], location=room, owner=t_wizard)
        torch = _make_flashlight(room, t_wizard)
        torch.set_property("alight", True)
        torch.set_placement("under", rug)
        assert torch not in room.get_lights()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_lights_finds_inventory_light(t_init: Object, t_wizard: Object):
    """A lit flashlight in the wizard's inventory is returned by get_lights."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        torch = _make_flashlight(t_wizard, t_wizard)
        torch.set_property("alight", True)
        assert torch in room.get_lights()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_carried_flashlight_lights_dark_room(t_init: Object, t_wizard: Object):
    """A lit flashlight in a player's inventory makes a dark room lit."""
    with code.ContextManager(t_wizard, lambda s: None):
        room = setup_room(t_wizard)
        room.set_property("dark", True)
        torch = _make_flashlight(t_wizard, t_wizard)
        assert room.is_lit() is False
        torch.set_property("alight", True)
        assert room.is_lit() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_attributes_light_source(t_init: Object, t_wizard: Object):
    """In a dark-but-lit room, tell_contents prints which object provides the light."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        room.set_property("dark", True)
        torch = _make_flashlight(room, t_wizard, name="brass flashlight")
        torch.set_property("alight", True)
        printed.clear()
        parse.interpret(ctx, "look")
    assert any("lit by" in line.lower() and "brass flashlight" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_no_attribution_when_not_dark(t_init: Object, t_wizard: Object):
    """A normally-lit room does not mention a light source even if one is alight."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        torch = _make_flashlight(room, t_wizard, name="brass flashlight")
        torch.set_property("alight", True)
        printed.clear()
        parse.interpret(ctx, "look")
    assert not any("lit by" in line.lower() for line in printed)
