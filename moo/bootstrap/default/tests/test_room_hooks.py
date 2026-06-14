"""Tests for overridable room-rendering hooks (spec 200, item A).

Each hook has a default that preserves today's behavior; a per-room override
changes one aspect of ``look_self`` / ``tell_contents`` without copying the verb.
"""

import warnings

import pytest

from moo.core import code, create
from moo.core.models import Object
from moo.sdk import lookup


def _room(name="Hook Room"):
    room = create(name, parents=[lookup("Generic Room")])
    room.set_property("description", "A plain test room.")
    return room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_default_description_and_compass(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = _room()
        room.look_self()
    out = "\n".join(printed)
    assert "Hook Room" in out
    assert "A plain test room." in out
    # Default compass is drawn (arrow glyphs present).
    assert "↑" in out  # ↑


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_description_override(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = _room("Custom Room")
        room.add_verb("look_description", code="return 'HOOK-SOURCED DESCRIPTION'")
        room.look_self()
    out = "\n".join(printed)
    assert "HOOK-SOURCED DESCRIPTION" in out
    assert "A plain test room." not in out


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_show_compass_override_hides_compass(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = _room("No Compass Room")
        room.add_verb("show_compass", code="return False")
        room.look_self()
    out = "\n".join(printed)
    assert "No Compass Room" in out
    assert "A plain test room." in out
    assert "↑" not in out  # no compass arrows


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_hide_from_contents_override(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = _room("Scenery Room")
        widget = create("widget", location=room)
        widget.obvious = True
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            widget.save()
        # Default: the widget is listed.
        room.tell_contents()
        assert any("widget" in p for p in printed)
        # Override: hide everything the room renders itself.
        printed.clear()
        room.add_verb("hide_from_contents", code="return True", direct_object="any")
        room.tell_contents()
        assert not any("widget" in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_extra_override(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = _room("Sectioned Room")
        room.add_verb("tell_contents_extra", code="print('-- Points of Interest --')")
        room.tell_contents()
    assert any("Points of Interest" in p for p in printed)
