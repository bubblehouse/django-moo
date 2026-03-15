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
    """emote sends 'You <action>' to the caller."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in caught.list]
    assert any("(Wizard)): You waves hello." in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_emote_others_see_action(t_init: Object, t_wizard: Object):
    """emote sends the action text to others in the room via announce."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in caught.list]
    assert any("(Player)): waves hello." in m for m in messages)


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
