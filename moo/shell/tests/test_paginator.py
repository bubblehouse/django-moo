# -*- coding: utf-8 -*-

import pytest

from moo.core import code, create, lookup, open_paginator
from moo.core.exceptions import UserError
from moo.core.models import Object


# ---------------------------------------------------------------------------
# Helper verb bodies
# ---------------------------------------------------------------------------

_TRIGGER_VERB = """\
from moo.core import context, open_paginator
open_paginator(context.player, "hello\\nworld")
"""

_TRIGGER_VERB_PYTHON = """\
from moo.core import context, open_paginator
open_paginator(context.player, "def foo():\\n    pass", content_type="python")
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_paginator_publishes_paginator_event(t_init: Object, t_wizard: Object):
    """Invoking a verb that calls open_paginator() publishes a paginator event dict
    to the player's Kombu queue (emitted as a RuntimeWarning in tests)."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("paginator_test", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("trigger_page", code=_TRIGGER_VERB)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_page")

    messages = [str(warning.message) for warning in w.list]
    assert any("'event': 'paginator'" in m for m in messages)
    assert any("hello" in m for m in messages)
    assert any("'content_type': 'text'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_paginator_python_content_type(t_init: Object, t_wizard: Object):
    """content_type='python' is passed through to the paginator event dict."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("paginator_test_py", parents=[t_init.root_class], location=t_wizard.location)
        obj.add_verb("trigger_page", code=_TRIGGER_VERB_PYTHON)

        with pytest.warns(RuntimeWarning) as w:
            obj.invoke_verb("trigger_page")

    messages = [str(warning.message) for warning in w.list]
    assert any("'content_type': 'python'" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_paginator_invalid_content_type_raises(t_init: Object, t_wizard: Object):
    """open_paginator() raises UserError for an unrecognised content_type."""
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.raises(UserError):
            open_paginator(t_wizard, "some text", content_type="xml")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_paginator_non_wizard_raises(t_init: Object, t_wizard: Object):
    """open_paginator() raises UserError when the caller is not a wizard."""
    player_npc = lookup("Player")
    with code.ContextManager(player_npc, lambda _: None):
        with pytest.raises(UserError):
            open_paginator(player_npc, "some text")
