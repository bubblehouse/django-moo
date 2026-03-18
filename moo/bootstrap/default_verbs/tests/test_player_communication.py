import pytest

from moo.core import code, parse
from moo.sdk import lookup
from moo.core.models import Object

# --- message verbs ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_absent_msg(t_init: Object, t_wizard: Object):
    """page_absent_msg() returns a string containing the player's name."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_absent_msg()
    assert "Wizard" in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_origin_msg(t_init: Object, t_wizard: Object):
    """page_origin_msg() returns a string with the player's name and location."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_origin_msg()
    assert "Wizard" in result
    assert "The Laboratory" in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_echo_msg(t_init: Object, t_wizard: Object):
    """page_echo_msg() returns the echo confirmation string."""
    with code.ContextManager(t_wizard, lambda _: None):
        result = t_wizard.page_echo_msg()
    assert result == "Your message has been sent."


# --- page ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_sends_origin_msg(t_init: Object, t_wizard: Object):
    """page <player> sends the page_origin_msg to the recipient via tell."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "page Player")
    messages = [str(x.message) for x in w.list]
    assert any("Wizard" in m and "The Laboratory" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_with_message(t_init: Object, t_wizard: Object):
    """page <player> with <message> sends the origin msg and the message to the recipient."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "page Player with Hello there")
    messages = [str(x.message) for x in w.list]
    assert any("Wizard" in m for m in messages)
    assert any('pages, "Hello there"' in m for m in messages)


# --- whisper ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whisper_sends_message(t_init: Object, t_wizard: Object):
    """whisper <message> to <player> delivers the whisper to the recipient via write()."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.warns(RuntimeWarning, match="whispers to you"):
            parse.interpret(ctx, "whisper Hello to Player")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_whisper_no_caller_echo(t_init: Object, t_wizard: Object):
    """whisper delivers to the recipient but sends no echo to the caller."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with pytest.warns(RuntimeWarning, match="whispers to you"):
            parse.interpret(ctx, "whisper Hello to Player")
    assert not printed


# --- page ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_page_sends_caller_echo(t_init: Object, t_wizard: Object):
    """page sends the page_echo_msg confirmation back to the caller via print()."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "page Player")
    assert "Your message has been sent." in printed


# --- announce ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_announce_delegates_to_room(t_init: Object, t_wizard: Object):
    """announce() delegates to the location's announce verb when it exists."""
    player_npc = lookup("Player")
    player_npc.location = t_wizard.location
    player_npc.save()
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.warns(RuntimeWarning) as w:
            t_wizard.announce("hello from wizard")
    messages = [str(x.message) for x in w.list]
    assert any("hello from wizard" in m for m in messages)
