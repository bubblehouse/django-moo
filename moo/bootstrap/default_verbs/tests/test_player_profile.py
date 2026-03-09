import pytest

from moo.core import code, create, lookup, parse
from moo.core.models import Object


# --- @describe ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_sets_description(t_init: Object, t_wizard: Object, setup_item):
    """@describe <obj> as <text> sets the description on the object."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        parse.interpret(ctx, "@describe widget as A shiny widget.")
        widget.refresh_from_db()
    assert widget.description() == "[deep_sky_blue1]A shiny widget.[/deep_sky_blue1]"
    assert any("Description set for" in line for line in printed)


# --- look_self ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_shows_sleeping(t_init: Object, t_wizard: Object):
    """look_self() on a player prints a sleeping status message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.look_self()
    assert any("sleeping" in line for line in printed)


# --- @password ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_not_implemented(t_init: Object, t_wizard: Object):
    """@password prints a not-yet-implemented message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@password")
    assert "@password is not yet implemented." in printed


# --- confunc / disfunc ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_runs_without_error(t_init: Object, t_wizard: Object):
    """confunc() runs without raising an exception."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.confunc()
    assert result is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_disfunc_runs_without_error(t_init: Object, t_wizard: Object):
    """disfunc() runs without raising an exception."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.disfunc()
    assert result is None


# --- @gripe ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gripe_not_implemented(t_init: Object, t_wizard: Object):
    """@gripe prints a not-yet-implemented message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@gripe something")
    assert "@gripe is not yet implemented." in printed


# --- news ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_news_not_implemented(t_init: Object, t_wizard: Object):
    """news prints a not-yet-implemented message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "news")
    assert "news is not yet implemented." in printed


# --- @gender ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gender_no_arg_shows_current(t_init: Object, t_wizard: Object):
    """@gender without an argument prints the player's current gender and pronouns."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@gender")
    assert any("Current gender:" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gender_set_gender(t_init: Object, t_wizard: Object):
    """@gender <gender> sets the player's gender and pronouns via gender_utils."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@gender male")
    assert any("Gender set to" in line for line in printed)


# --- @messages ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_messages_no_msg_props(t_init: Object, t_wizard: Object):
    """@messages on an object with no _msg properties prints nothing."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        sys = lookup(1)
        create("widget", parents=[sys.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@messages widget")
    assert not any(line.endswith("_msg") or "_msg:" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_messages_shows_msg_props(t_init: Object, t_wizard: Object, setup_item):
    """@messages lists properties whose names end in _msg."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_item(t_wizard.location, "widget")
        widget.set_property("test_msg", "hello world")
        parse.interpret(ctx, "@messages widget")
    assert any("test_msg" in line and "hello world" in line for line in printed)
