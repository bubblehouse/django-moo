import pytest

from moo.core import code, parse
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_quit_publishes_disconnect(t_init: Object, t_wizard: Object):
    """@quit publishes a disconnect event to the player's message queue."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@quit")
    messages = [str(x.message) for x in w.list]
    assert any("disconnect" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_quit_prints_goodbye(t_init: Object, t_wizard: Object):
    """@quit prints a goodbye message containing the player's name."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@quit")
    assert any("Goodbye" in line and "Wizard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quit_fallback_prints_message(t_init: Object, t_wizard: Object):
    """QUIT with no room override prints a redirect to @quit."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "QUIT")
    assert any("@quit" in line for line in printed)
