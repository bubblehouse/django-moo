"""Tests for the on_player_action event hook (spec 200, item C)."""

import pytest

from moo.core import code, create, parse
from moo.core.models import Object
from moo.sdk import lookup

from .utils import setup_room, save_quietly

# A subscriber override that records every (action, object) it observes.
_RECORDER = """
log = this.get_property('action_log') if this.has_property('action_log') else []
log.append([args[1], args[2].get('object')])
this.set_property('action_log', log)
"""


def _thing(location, name="gadget"):
    item = create(name, parents=[lookup("Generic Thing")], location=location)
    item.obvious = True
    save_quietly(item)
    return item


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_emits_action(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        room = setup_room(t_wizard)
        gadget = _thing(room)
        t_wizard.add_verb("on_player_action", code=_RECORDER, direct_object="any")
        parse.interpret(ctx, "take gadget")
        log = t_wizard.get_property("action_log")
    assert ["take", gadget.id] in log


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_emits_action(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        room = setup_room(t_wizard)
        gadget = _thing(room)
        t_wizard.add_verb("on_player_action", code=_RECORDER, direct_object="any")
        parse.interpret(ctx, "take gadget")
        parse.interpret(ctx, "drop gadget")
        log = t_wizard.get_property("action_log")
    assert ["take", gadget.id] in log
    assert ["drop", gadget.id] in log


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_failed_take_does_not_emit(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        room = setup_room(t_wizard)
        gadget = _thing(room)
        t_wizard.add_verb("on_player_action", code=_RECORDER, direct_object="any")
        parse.interpret(ctx, "take gadget")  # success
        parse.interpret(ctx, "take gadget")  # already held -> no new event
        log = t_wizard.get_property("action_log")
    assert log.count(["take", gadget.id]) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_default_hook_is_noop(t_init: Object, t_wizard: Object):
    # With no override, taking succeeds and nothing is recorded (no error).
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        room = setup_room(t_wizard)
        gadget = _thing(room)
        parse.interpret(ctx, "take gadget")
        gadget.refresh_from_db()
        assert gadget.location == t_wizard
        assert not t_wizard.has_property("action_log")
