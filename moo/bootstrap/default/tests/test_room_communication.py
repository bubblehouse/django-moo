import pytest

from moo.core import code, parse
from moo.sdk import lookup
from moo.core.models import Object
from .utils import save_quietly, setup_room

# --- say ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_say_delivers_to_caller_and_others(t_init: Object, t_wizard: Object):
    """say sends 'You: msg' to the caller and 'Name: msg' to others in the room."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "say Hello there!")
    messages = [str(w.message) for w in caught.list]
    assert any("(Wizard)): You: Hello there!" in m for m in messages)
    assert any("(Player)): Wizard: Hello there!" in m for m in messages)


# --- emote ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_emote_caller_sees_own_action(t_init: Object, t_wizard: Object):
    """emote shows the caller their own line, with their name first."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in caught.list]
    assert any("(Wizard)): Wizard waves hello." in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_emote_others_see_action(t_init: Object, t_wizard: Object):
    """emote shows others the line with the actor's name first, so no one can pose as another player."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in caught.list]
    assert any("(Player)): Wizard waves hello." in m for m in messages)
    assert not any("(Player)): waves hello." in m for m in messages)


# --- announce ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_skips_caller(t_init: Object, t_wizard: Object):
    """announce() does not deliver the message to the caller."""
    received_by_wizard = []
    with code.ContextManager(t_wizard, received_by_wizard.append):
        room = setup_room(t_wizard)
        room.announce("secret message")
    assert not any("secret message" in line for line in received_by_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_delivers_to_others(t_init: Object, t_wizard: Object):
    """announce() sends the message to every room occupant except the caller."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            room.announce("broadcast message")
    messages = [str(x.message) for x in w.list]
    assert any("(Player)): broadcast message" in m for m in messages)
    assert not any("(Wizard)): broadcast message" in m for m in messages)


# --- announce_all ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_all_delivers_to_everyone(t_init: Object, t_wizard: Object):
    """announce_all() sends the message to every occupant including the caller."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            room.announce_all("all hands message")
    messages = [str(x.message) for x in w.list]
    assert any("(Wizard)): all hands message" in m for m in messages)
    assert any("(Player)): all hands message" in m for m in messages)


# --- announce_all_but ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_all_but_skips_specified_object(t_init: Object, t_wizard: Object):
    """announce_all_but() skips exactly the specified object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            room.announce_all_but(player, "exclusive message")
    messages = [str(x.message) for x in w.list]
    assert any("(Wizard)): exclusive message" in m for m in messages)
    assert not any("(Player)): exclusive message" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_all_but_delivers_to_rest(t_init: Object, t_wizard: Object):
    """announce_all_but() delivers the message to all non-excluded occupants."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            room.announce_all_but(t_wizard, "player only message")
    messages = [str(x.message) for x in w.list]
    assert any("(Player)): player only message" in m for m in messages)
    assert not any("(Wizard)): player only message" in m for m in messages)


# --- mute ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_muted_player_speech_reaches_no_one(t_init: Object, t_wizard: Object):
    """A muted account's say, emote, page, and whisper reach no one; @unmute restores them."""
    from moo.sdk import account_for, is_muted  # pylint: disable=import-outside-toplevel

    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        parse.interpret(ctx, "@mute Player for 2")
    assert is_muted(account_for(player))
    for line in ("say hello", "emote waves", "page Wizard with hi", "whisper psst to Wizard"):
        with code.ContextManager(player, lambda msg: None) as ctx:
            with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
                parse.interpret(ctx, line)
        messages = [str(w.message) for w in caught.list]
        assert any("(Player)): You are muted." in m for m in messages), (line, messages)
        assert not any("(Wizard))" in m for m in messages), (line, messages)
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        parse.interpret(ctx, "@unmute Player")
    assert not is_muted(account_for(player))
    with code.ContextManager(player, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "say hello again")
    assert any("(Wizard)): Player: hello again" in str(w.message) for w in caught.list)


# --- report ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_report_records_the_target_and_reaches_staff(t_init: Object, t_wizard: Object):
    """report logs the target's account and room, and mails the gripe recipients."""
    from moo.core.models import AuditLog  # pylint: disable=import-outside-toplevel
    from moo.core.models.mail import MessageRecipient  # pylint: disable=import-outside-toplevel
    from moo.sdk import account_for  # pylint: disable=import-outside-toplevel

    player = lookup("Player")
    printed = []
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, "report Wizard")
        parse.interpret(ctx, "report Wizard for shouting in the lab")
    assert any("Say what happened" in str(line) for line in printed)
    assert any("The staff have your report" in str(line) for line in printed)
    row = AuditLog.objects.get(action="report")
    assert row.target_id == t_wizard.pk
    assert f"account {account_for(t_wizard).pk}" in row.detail
    assert "shouting in the lab" in row.detail
    assert MessageRecipient.objects.filter(recipient=t_wizard, message__subject__contains="report").exists()


# --- staff see accounts ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_staff_see_the_account_behind_a_name(t_init: Object, t_wizard: Object):
    """@whereis and @auditlog show a wizard the account id; @whereis hides it from a player."""
    from moo.sdk import account_for  # pylint: disable=import-outside-toplevel

    player = lookup("Player")
    account = account_for(player)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@whereis Player")
        parse.interpret(ctx, "@mute Player for 1")
        parse.interpret(ctx, "@auditlog")
    assert sum(f"(acct {account.pk})" in str(line) for line in printed) >= 2, printed
    printed = []
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, "@whereis Wizard")
    assert not any("acct" in str(line) for line in printed), printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_staff_commands_refuse_a_non_wizard(t_init: Object, t_wizard: Object):
    """A non-wizard cannot reach @mute, @unmute, @suspend, @ban, or @auditlog, even naming a wizard as an object."""
    from moo.core.models import Player as Account  # pylint: disable=import-outside-toplevel
    from moo.sdk import account_for, is_muted  # pylint: disable=import-outside-toplevel

    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        parse.interpret(ctx, "@mute Player for 1")
    for line in (
        "@unmute Player for Wizard",
        "@suspend Player for Wizard",
        "@ban Player for Wizard",
        "@auditlog Wizard",
    ):
        printed = []
        with code.ContextManager(player, printed.append) as ctx:
            try:
                parse.interpret(ctx, line)
            except Exception:  # pylint: disable=broad-except
                pass
        assert not any("acct" in str(p) for p in printed), (line, printed)
    account = account_for(player)
    account.refresh_from_db()
    assert is_muted(account)
    assert account.status == Account.STATUS_ACTIVE


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_report_handles_a_missing_target_and_markup(t_init: Object, t_wizard: Object):
    """An unknown target gets a hint; markup in the reason is neutralised."""
    from moo.core.models import AuditLog  # pylint: disable=import-outside-toplevel

    player = lookup("Player")
    printed = []
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, "report Nobodyatall for spam")
        parse.interpret(ctx, "report here for [bold]loud[/bold] noises")
    assert any("There is no one by that name" in str(line) for line in printed)
    row = AuditLog.objects.get(action="report")
    assert "[bold]" not in row.detail and "(bold)loud" in row.detail
