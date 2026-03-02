import pytest

from moo.core import code, lookup, parse
from moo.core.models import Object


# --- @sethome ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sethome_sets_home(t_init: Object, t_wizard: Object):
    """@sethome sets the player's home property to their current location."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        location = t_wizard.location
        parse.interpret(ctx, "@sethome")
        t_wizard.refresh_from_db()
    assert t_wizard.get_property("home") == location
    assert any("home has been set" in line for line in printed)


@pytest.mark.skip(reason="requires creating a room whose accept() returns False")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sethome_rejects_non_accepting_room(t_init: Object, t_wizard: Object):
    """@sethome prints an error when the current room does not accept the player."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@sethome")
    assert any("not allowing you to enter" in line for line in printed)


# --- home ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_home_already_there(t_init: Object, t_wizard: Object):
    """home prints 'already at home' when the player is already at their home location."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        t_wizard.set_property("home", t_wizard.location)
        parse.interpret(ctx, "home")
    assert any("already at home" in line for line in printed)


@pytest.mark.skip(reason="depends on player.moveto() verb being callable from Python")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_home_moves_player(t_init: Object, t_wizard: Object):
    """home teleports the player to their home location."""
    pass


@pytest.mark.skip(reason="depends on player.moveto() verb being callable from Python")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_home_not_set(t_init: Object, t_wizard: Object):
    """home sets the player's home to $player_start when none is configured."""
    pass


# --- @move ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_item_to_location(t_init: Object, t_wizard: Object, setup_item):
    """@move <item> to <location> changes the item's location."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = setup_item(t_wizard, "widget")
        parse.interpret(ctx, "@move widget to The Laboratory")
        widget.refresh_from_db()
    assert widget.location.name == "The Laboratory"


@pytest.mark.skip(reason="moving a player uses _.string_utils.pronoun_sub() for arrival/departure messages; not yet verified")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_player_teleport(t_init: Object, t_wizard: Object):
    """@move <player> to <location> teleports the player and prints arrival/departure messages."""
    pass


# --- @dig ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_dig_creates_room_and_exit(t_init: Object, t_wizard: Object):
    """@dig <direction> to <name> creates a new room and an exit from the current room."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "@dig north to New Room")
        t_wizard.refresh_from_db()
    assert lookup("New Room") is not None
    assert t_wizard.location.match_exit("north") is not None


@pytest.mark.skip(reason="@tunnel requires multi-step setup and _.string_utils.pronoun_sub usage not yet verified")
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tunnel_to_existing_room(t_init: Object, t_wizard: Object):
    """@tunnel <direction> to <existing room> creates an exit without creating a new room."""
    pass
