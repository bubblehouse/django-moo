import warnings

import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sethome_rejects_non_accepting_room(t_init: Object, t_wizard: Object):
    """@sethome prints an error when the current room does not accept the player."""
    system = lookup(1)
    player_npc = lookup("Player")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        locked_room = create("Restricted Room", parents=[system.room], location=None)
        locked_room.owner = player_npc
        locked_room.save()
        locked_room.set_property("free_entry", False)
        Object.objects.filter(pk=t_wizard.pk).update(location=locked_room)
        t_wizard.refresh_from_db()
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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_home_moves_player(t_init: Object, t_wizard: Object):
    """home teleports the player to their home location."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        second_room = create("Home Room", parents=[system.room], location=None)
        t_wizard.set_property("home", second_room)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            parse.interpret(ctx, "home")
        t_wizard.refresh_from_db()
    assert t_wizard.location == second_room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_home_not_set(t_init: Object, t_wizard: Object):
    """home sets the player's home to $player_start when none is configured."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "home")
        t_wizard.refresh_from_db()
    system = lookup(1)
    assert t_wizard.get_property("home") == system.player_start
    assert any("home was not set" in line for line in printed)


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_player_teleport(t_init: Object, t_wizard: Object):
    """@move <player> to <location> teleports the player and sends departure/arrival messages."""
    system = lookup(1)
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        _second_room = create("Destination", parents=[system.room], location=None)
        with pytest.warns(RuntimeWarning) as caught:
            parse.interpret(ctx, "@move Wizard to Destination")
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in caught.list]
    assert any("Wizard disappears suddenly" in m and str(player_npc.pk) in m for m in messages)
    assert t_wizard.location.name == "Destination"


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tunnel_to_existing_room(t_init: Object, t_wizard: Object):
    """@tunnel <direction> to <existing room> creates an exit without creating a new room."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        existing_room = create("Far Away", parents=[system.room], location=None)
        parse.interpret(ctx, "@tunnel east to Far Away")
        t_wizard.refresh_from_db()
    assert t_wizard.location.match_exit("east") is not None
    assert lookup("Far Away").id == existing_room.id


# --- teleport ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_teleport_moves_player(t_init: Object, t_wizard: Object):
    """teleport #N moves the player directly to the target room."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        dest = create("The Observatory", parents=[system.room], location=None)
        parse.interpret(ctx, f"teleport #{dest.pk}")
        t_wizard.refresh_from_db()
    assert t_wizard.location.pk == dest.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_teleport_rejects_non_room(t_init: Object, t_wizard: Object, setup_item):
    """teleport prints an error when the target object is not a room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        item = setup_item(t_wizard, "widget")
        original_location = t_wizard.location
        parse.interpret(ctx, f"teleport #{item.pk}")
        t_wizard.refresh_from_db()
    assert any("not a room" in line.lower() for line in printed)
    assert t_wizard.location.pk == original_location.pk
