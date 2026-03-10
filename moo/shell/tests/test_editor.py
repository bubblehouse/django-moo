# -*- coding: utf-8 -*-

import pytest

from moo.core import code, create, lookup, open_editor
from moo.core.exceptions import UserError
from moo.core.models import Object


# ---------------------------------------------------------------------------
# Helper verb bodies
# ---------------------------------------------------------------------------

# Trigger verb: opens an editor pre-filled with "hello\nworld", wiring the
# callback verb on the same object to receive the saved text.
_TRIGGER_VERB = """\
from moo.core import context, open_editor
callback = this.get_verb("edit_callback")
open_editor(context.player, "hello\\nworld", callback)
"""

# Trigger verb variant that passes content_type="python".
_TRIGGER_VERB_PYTHON = """\
from moo.core import context, open_editor
callback = this.get_verb("edit_callback")
open_editor(context.player, "def foo():\\n    pass", callback, content_type="python")
"""

# Callback verb: receives the edited text as args[0] and prints it.
_CALLBACK_VERB = "print(args[0])"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_publishes_editor_event(t_init: Object, t_wizard: Object):
    """Invoking a verb that calls open_editor() publishes an editor event dict
    to the player's Kombu queue (emitted as a RuntimeWarning in tests)."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test", parents=[lookup(1).root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        obj.add_verb("trigger_edit", code=_TRIGGER_VERB)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_edit")

    messages = [str(warning.message) for warning in w.list]
    assert any("'event': 'editor'" in m for m in messages)
    assert any("hello" in m for m in messages)
    assert any("edit_callback" in m for m in messages)
    assert any("'content_type': 'text'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_python_content_type(t_init: Object, t_wizard: Object):
    """content_type='python' is passed through to the editor event dict."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_py", parents=[lookup(1).root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        obj.add_verb("trigger_edit", code=_TRIGGER_VERB_PYTHON)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_edit")

    messages = [str(warning.message) for warning in w.list]
    assert any("'content_type': 'python'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_invalid_content_type_raises(t_init: Object, t_wizard: Object):
    """open_editor() raises UserError for an unrecognised content_type."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_err", parents=[lookup(1).root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        callback = obj.get_verb("edit_callback")

        with pytest.raises(UserError):
            open_editor(t_wizard, "some text", callback, content_type="xml")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_editor_non_wizard_raises(t_init: Object, t_wizard: Object):
    """open_editor() raises UserError when the caller is not a wizard."""
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("editor_test_perm", parents=[lookup(1).root_class], location=t_wizard.location)
        obj.add_verb("edit_callback", code=_CALLBACK_VERB)
        callback = obj.get_verb("edit_callback")

    # Re-enter as the non-wizard player
    with code.ContextManager(player_npc, lambda _: None):
        with pytest.raises(UserError):
            open_editor(player_npc, "some text", callback)
