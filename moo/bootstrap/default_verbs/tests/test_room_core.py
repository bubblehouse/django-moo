import warnings

import pytest

from moo.core import code, exceptions, parse
from moo.sdk import context, create, lookup
from moo.core.models import Object, Player
from .utils import save_quietly, setup_room, setup_root_item


# --- look_self ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_prints_room_name(t_init: Object, t_wizard: Object):
    """look_self() prints the room name in bright_yellow."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        room.look_self()
    assert f"[bright_yellow]{room.name}[/bright_yellow]" in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_prints_description(t_init: Object, t_wizard: Object):
    """look_self() prints the room description via passthrough."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard, description="A damp cave draped in shadows.")
        room.look_self()
    assert room.description() in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_includes_contents(t_init: Object, t_wizard: Object):
    """look_self() calls tell_contents so room items appear in output."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        setup_root_item(room, "gold coin")
        room.look_self()
    assert any("gold coin" in line for line in printed)


# --- tell_contents: ctype 3 (default) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_empty(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 prints nothing when the room is empty."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Empty Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        room.tell_contents()
    assert not printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_single_item(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 prints a single non-player item."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("One Item Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert printed == ["You see red ball here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_multiple_items(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 lists multiple non-player items."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Multi Item Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        setup_root_item(room, "red ball")
        setup_root_item(room, "blue box")
        room.tell_contents()
    assert printed == ["You see red ball and blue box here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_single_player(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 prints a single player."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Player Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        t_wizard.location = room
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        room.tell_contents()
    assert printed == ["You see Player here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_multiple_players(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 lists multiple players with 'are here'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Two Player Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            t_wizard.location = room
            t_wizard.save()
            context.caller.refresh_from_db()
            player = lookup("Player")
            player.location = room
            player.save()
            bob = create("Bob", location=room)
        Player.objects.create(avatar=bob)
        room.tell_contents()
    assert printed == ["Player and Bob are here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_mixed(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 prints items and players on separate lines."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Mixed Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            t_wizard.location = room
            t_wizard.save()
            context.caller.refresh_from_db()
            setup_root_item(room, "red ball")
            player = lookup("Player")
            player.location = room
            player.save()
        room.tell_contents()
    assert printed == ["You see red ball here.", "You see Player here."]


# --- tell_contents: ctype 2 ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype2_single_item(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=2 prints a single item."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Ctype2 Room", parents=[rooms])
        room.set_property("content_list_type", 2)
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert printed == ["You see red ball here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype2_mixed(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=2 lists players and items together."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Ctype2 Mixed Room", parents=[rooms])
        room.set_property("content_list_type", 2)
        t_wizard.location = room
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert printed == ["You see Player and red ball here."]


# --- tell_contents: ctype 1 ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype1(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=1 prints one line per object."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Ctype1 Room", parents=[rooms])
        room.set_property("content_list_type", 1)
        t_wizard.location = room
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert printed == ["Player is here", "You see red ball here"]


# --- tell_contents: ctype 0 ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype0(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=0 prints a raw Contents: list."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Ctype0 Room", parents=[rooms])
        room.set_property("content_list_type", 0)
        t_wizard.location = room
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert printed == ["Contents:", "red ball"]


# --- tell_contents: out-of-range ctype ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype_out_of_range(t_init: Object, t_wizard: Object):
    """tell_contents() with an unrecognised ctype prints nothing."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Silent Room", parents=[rooms])
        room.set_property("content_list_type", 99)
        setup_root_item(room, "red ball")
        room.tell_contents()
    assert not printed


# --- confunc ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_shows_room_to_player(t_init: Object, t_wizard: Object):
    """confunc() displays the room's look_self output to the connecting player."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        room.confunc()
    assert f"[bright_yellow]{room.name}[/bright_yellow]" in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_announces_connection_to_others(t_init: Object, t_wizard: Object):
    """confunc() tells everyone else in the room that the player has connected."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        save_quietly(player)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            room.confunc()
    messages = [str(x.message) for x in w.list]
    assert any("has connected" in m and str(t_wizard) in m for m in messages)


# --- disfunc ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_disfunc_moves_player_to_home(t_init: Object, t_wizard: Object):
    """disfunc() teleports the player to their home when they are elsewhere."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        away = create("Away Room", parents=[rooms])
        t_player = lookup("Player")
        t_player.location = away
        save_quietly(t_player)
        t_wizard.location = away
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            t_wizard.location.disfunc()
        t_wizard.refresh_from_db()
    messages = [str(x.message) for x in w.list]
    assert any(f"(Player)): #{t_wizard.pk} (Wizard) has disconnected." in m for m in messages)
    system = lookup(1)
    assert t_wizard.location == system.player_start


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_disfunc_noop_when_already_home(t_init: Object, t_wizard: Object):
    """disfunc() does nothing when the player is already at their home."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        t_wizard.location = system.player_start
        t_wizard.save()
        context.caller.refresh_from_db()
        home_before = system.player_start
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            t_wizard.location.disfunc()
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in caught.list]
    assert any(f"(Player)): #{t_wizard.pk} (Wizard) has disconnected." in m for m in messages)
    assert t_wizard.location == home_before


# --- accept ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_free_entry_allows_any_object(t_init: Object, t_wizard: Object):
    """accept() returns True when the room's free_entry property is set."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        room = create("Open Room", parents=[rooms])
        room.set_property("free_entry", True)
        item = setup_root_item(t_wizard.location)
        assert room.accept(item) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_owner_match_allows_entry(t_init: Object, t_wizard: Object):
    """accept() returns True when the object's owner matches the room's owner."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        room = create("Owned Room", parents=[rooms])
        room.set_property("free_entry", False)
        # wizard owns both the room and the item by default
        item = setup_root_item(t_wizard.location)
        assert room.accept(item) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_locked_room_denies_entry(t_init: Object, t_wizard: Object):
    """accept() returns False when the room is locked against the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        room = create("Locked Room", parents=[rooms])
        room.set_property("free_entry", False)
        item = setup_root_item(t_wizard.location)
        # Point the key at the room itself — the item won't satisfy that lock
        room.set_property("key", room)
        assert room.accept(item) is False


# --- match_exit ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_exit_found_by_name(t_init: Object, t_wizard: Object):
    """match_exit() returns the exit object when matched by direction name."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@dig north to Destination Room")
        exit_obj = t_wizard.location.match_exit("north")
    assert exit_obj is not None
    assert exit_obj.dest.name == "Destination Room"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_exit_not_found_returns_none(t_init: Object, t_wizard: Object):
    """match_exit() returns None when no exit matches the given direction."""
    with code.ContextManager(t_wizard, lambda msg: None):
        result = t_wizard.location.match_exit("south")
    assert result is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_exit_case_insensitive(t_init: Object, t_wizard: Object):
    """match_exit() matches direction names case-insensitively."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@dig east to East Wing")
        exit_obj = t_wizard.location.match_exit("EAST")
    assert exit_obj is not None


# --- describe ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_sets_description_on_room(t_init: Object, t_wizard: Object):
    """room.describe() stores the given string as the room's description property."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        room.describe("A dank pit of sadness and mediocrity.")
        assert room.get_property("description") == "A dank pit of sadness and mediocrity."


# --- match_object ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_found_in_room(t_init: Object, t_wizard: Object):
    """match_object() returns the object when it is in the room."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        coin = setup_root_item(room, "silver coin")
        result = room.match_object("silver coin")
    assert result == coin


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_not_found_raises(t_init: Object, t_wizard: Object):
    """match_object() raises NoSuchObjectError when nothing matches the name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        with pytest.raises(exceptions.NoSuchObjectError):
            room.match_object("invisible thing")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_ambiguous_raises(t_init: Object, t_wizard: Object):
    """match_object() raises AmbiguousObjectError when multiple objects share a name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        setup_root_item(room, "red key")
        setup_root_item(room, "red key")
        with pytest.raises(exceptions.AmbiguousObjectError):
            room.match_object("red key")
