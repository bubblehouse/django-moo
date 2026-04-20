import datetime
from unittest.mock import patch

import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
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
    """look_self() on a disconnected player prints a sleeping status message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.look_self()
    assert any("sleeping" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_shows_alert(t_init: Object, t_wizard: Object):
    """look_self() on a recently active player prints an alert status message."""
    now = datetime.datetime.now(datetime.timezone.utc)
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.set_property("last_connected_time", now)
        t_wizard.look_self()
    assert any("awake and looks alert" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_shows_idle(t_init: Object, t_wizard: Object):
    """look_self() on an idle connected player prints a staring-off message."""
    two_minutes_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        t_wizard.set_property("last_connected_time", two_minutes_ago)
        t_wizard.look_self()
    assert any("staring off into space" in line for line in printed)


# --- @password ---


@pytest.fixture
def t_player_with_password(t_wizard):
    from moo.core.models.auth import Player  # pylint: disable=import-outside-toplevel

    player_record = Player.objects.get(avatar=t_wizard)
    player_record.user.set_password("OldPassword1!")
    player_record.user.save()
    return player_record.user


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_changes_via_confirm_callback(t_init, t_wizard, t_player_with_password):
    """at_password_confirm changes the password when old password and confirmation match."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        confirm_cb = t_wizard.get_verb("at_password_confirm")
        confirm_cb("NewPassword2@", "OldPassword1!", "NewPassword2@")
    t_player_with_password.refresh_from_db()
    assert t_player_with_password.check_password("NewPassword2@")
    assert "Password changed." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_rejects_wrong_old(t_init, t_wizard, t_player_with_password):
    """at_password_confirm raises UserError when old password is wrong."""
    from moo.core.exceptions import UserError  # pylint: disable=import-outside-toplevel

    with code.ContextManager(t_wizard, lambda _: None):
        confirm_cb = t_wizard.get_verb("at_password_confirm")
        with pytest.raises(UserError, match="Incorrect old password"):
            confirm_cb("NewPassword2@", "WrongOld", "NewPassword2@")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_rejects_mismatch(t_init, t_wizard, t_player_with_password):
    """at_password_confirm prints error when new password and confirmation differ."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        confirm_cb = t_wizard.get_verb("at_password_confirm")
        confirm_cb("Different3!", "OldPassword1!", "NewPassword2@")
    assert any("do not match" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_wizard_bypass_old(t_init, t_wizard, t_player_with_password):
    """Wizard can change password by passing empty string for old password."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        confirm_cb = t_wizard.get_verb("at_password_confirm")
        confirm_cb("NewPassword3#", "", "NewPassword3#")
    t_player_with_password.refresh_from_db()
    assert t_player_with_password.check_password("NewPassword3#")
    assert "Password changed." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_entry_emits_input_prompt(t_init, t_wizard):
    """@password publishes an input_prompt event to open the old-password prompt."""
    with pytest.warns(RuntimeWarning, match="ConnectionError") as caught:
        with code.ContextManager(t_wizard, lambda _: None) as ctx:
            parse.interpret(ctx, "@password")
    messages = [str(w.message) for w in caught.list]
    assert any("input_prompt" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_password_entry_records_event_in_cache(t_init, t_wizard):
    """parse_command records ``input_prompt`` in the cache so the shell can skip the prompt race."""
    import warnings
    from django.core.cache import cache
    from moo.core import tasks

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = tasks.parse_command.apply(args=[t_wizard.pk, "@password"])
    try:
        events = cache.get(f"moo:task_events:{result.id}")
        assert events == ["input_prompt"]
    finally:
        cache.delete(f"moo:task_events:{result.id}")


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
def test_gripe_opens_editor(t_init: Object, t_wizard: Object):
    """@gripe opens an editor to compose a message to gripe recipients."""
    with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
        with code.ContextManager(t_wizard, lambda _: None) as ctx:
            parse.interpret(ctx, "@gripe")
    messages = [str(w.message) for w in caught.list]
    assert any("editor" in m for m in messages)


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


# --- @who ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_who_prints_header(t_init: Object, t_wizard: Object):
    """@who prints the 'Connected players:' header when players are online."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with patch("moo.sdk.connected_players", return_value=[t_wizard]):
            parse.interpret(ctx, "@who")
    assert any("Connected" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_who_no_connected_players(t_init: Object, t_wizard: Object):
    """@who prints a 'no players' message when connected_players() returns empty."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with patch("moo.sdk.connected_players", return_value=[]):
            parse.interpret(ctx, "@who")
    assert any("No players" in line or "no players" in line for line in printed)


# --- @quit ---


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
