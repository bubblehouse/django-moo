import pytest

from moo.core import context, code, create, exceptions, lookup, parse
from moo.core.models import Object


def setup_room(t_wizard: Object, name: str = "Test Room", description: str = "A plain test room."):
    """Create a Generic Room, describe it, and move the wizard into it."""
    rooms = lookup("Generic Room")
    room = create(name, parents=[rooms])
    room.describe(description)
    t_wizard.location = room
    t_wizard.save()
    context.caller.refresh_from_db()
    return room


def setup_item(location: Object, name: str = "red ball"):
    """Create a plain root_class child object in the given location."""
    system = lookup(1)
    return create(name, parents=[system.root_class], location=location)


# --- look_self ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_self_prints_room_name(t_init: Object, t_wizard: Object):
    """look_self() prints the room name in bright_yellow."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        room.look_self()
    assert f"[color bright_yellow]{room.name}[/color bright_yellow]" in printed


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
        setup_item(room, "gold coin")
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
        setup_item(room, "red ball")
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
        setup_item(room, "red ball")
        setup_item(room, "blue box")
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
        t_wizard.save()
        context.caller.refresh_from_db()
        room.tell_contents()
    assert printed == ["You see Wizard here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_multiple_players(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 lists multiple players with 'are here'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Two Player Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        t_wizard.location = room
        t_wizard.save()
        context.caller.refresh_from_db()
        player = lookup("Player")
        player.location = room
        player.save()
        room.tell_contents()
    assert printed == ["Wizard and Player are here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_ctype3_mixed(t_init: Object, t_wizard: Object):
    """tell_contents() with ctype=3 prints items and players on separate lines."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        rooms = lookup("Generic Room")
        room = create("Mixed Room", parents=[rooms])
        room.set_property("content_list_type", 3)
        t_wizard.location = room
        t_wizard.save()
        context.caller.refresh_from_db()
        setup_item(room, "red ball")
        room.tell_contents()
    assert printed == ["You see red ball here.", "You see Wizard here."]


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
        setup_item(room, "red ball")
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
        t_wizard.save()
        context.caller.refresh_from_db()
        setup_item(room, "red ball")
        room.tell_contents()
    assert printed == ["You see Wizard and red ball here."]


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
        t_wizard.save()
        context.caller.refresh_from_db()
        setup_item(room, "red ball")
        room.tell_contents()
    assert printed == ["Wizard is here", "You see red ball here"]


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
        t_wizard.save()
        context.caller.refresh_from_db()
        setup_item(room, "red ball")
        room.tell_contents()
    assert printed == ["Contents:", "Wizard", "red ball"]


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
        setup_item(room, "red ball")
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
    assert f"[color bright_yellow]{room.name}[/color bright_yellow]" in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_announces_connection_to_others(t_init: Object, t_wizard: Object):
    """confunc() tells everyone else in the room that the player has connected."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        room = setup_room(t_wizard)
        player = lookup("Player")
        player.location = room
        player.save()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            room.confunc()
    messages = [str(w.message) for w in warnings.list]
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
        t_player.save()
        t_wizard.location = away
        t_wizard.save()
        context.caller.refresh_from_db()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            t_wizard.location.disfunc()
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in warnings.list]
    assert any(f"(Player)): #{t_wizard.pk} (Wizard) has disconnected." in m for m in messages)
    assert t_wizard.location == t_wizard.home


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
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            t_wizard.location.disfunc()
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in warnings.list]
    assert any(f"(Player)): #{t_wizard.pk} (Wizard) has disconnected." in m for m in messages)
    assert t_wizard.location == home_before


# --- look (player command) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_no_args_shows_current_room(t_init: Object, t_wizard: Object):
    """'look' with no arguments shows the current room's look_self."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        parse.interpret(ctx, "look")
    assert f"[color bright_yellow]{room.name}[/color bright_yellow]" in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_at_named_object(t_init: Object, t_wizard: Object):
    """'look <name>' shows the description of the named object in the room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        coin = setup_item(room, "gold coin")
        coin.describe("A shiny gold coin minted in ancient times.")
        parse.interpret(ctx, "look gold coin")
    assert any("ancient times" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_missing_object_prints_error(t_init: Object, t_wizard: Object):
    """'look <name>' prints an error when no matching object is present."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "look nonexistent thing")
    assert any("nonexistent thing" in line for line in printed)


# --- say ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_say_delivers_to_caller_and_others(t_init: Object, t_wizard: Object):
    """say sends 'You: msg' to the caller and 'Name: msg' to others in the room."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "say Hello there!")
    messages = [str(w.message) for w in warnings.list]
    assert any("(Wizard)): You: Hello there!" in m for m in messages)
    assert any("(Player)): Wizard: Hello there!" in m for m in messages)


# --- emote ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_emote_caller_sees_own_action(t_init: Object, t_wizard: Object):
    """emote sends 'You <action>' to the caller."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in warnings.list]
    assert any("(Wizard)): You waves hello." in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_emote_others_see_action(t_init: Object, t_wizard: Object):
    """emote sends the action text to others in the room via announce."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "emote waves hello.")
    messages = [str(w.message) for w in warnings.list]
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
        player.save()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            room.announce("broadcast message")
    messages = [str(w.message) for w in warnings.list]
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
        player.save()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            room.announce_all("all hands message")
    messages = [str(w.message) for w in warnings.list]
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
        player.save()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            room.announce_all_but(player, "exclusive message")
    messages = [str(w.message) for w in warnings.list]
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
        player.save()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            room.announce_all_but(t_wizard, "player only message")
    messages = [str(w.message) for w in warnings.list]
    assert any("(Player)): player only message" in m for m in messages)
    assert not any("(Wizard)): player only message" in m for m in messages)


# --- huh / huh2 ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_huh_unrecognised_command(t_init: Object, t_wizard: Object):
    """An unrecognised command triggers huh2, which tells the player 'Huh?'."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "xyzzy")
    messages = [str(w.message) for w in warnings.list]
    assert any("Huh?" in m for m in messages)


# --- accept ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_free_entry_allows_any_object(t_init: Object, t_wizard: Object):
    """accept() returns True when the room's free_entry property is set."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        room = create("Open Room", parents=[rooms])
        room.set_property("free_entry", True)
        item = setup_item(t_wizard.location)
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
        item = setup_item(t_wizard.location)
        assert room.accept(item) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_accept_locked_room_denies_entry(t_init: Object, t_wizard: Object):
    """accept() returns False when the room is locked against the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        rooms = lookup("Generic Room")
        room = create("Locked Room", parents=[rooms])
        room.set_property("free_entry", False)
        item = setup_item(t_wizard.location)
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


# --- match_object ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_found_in_room(t_init: Object, t_wizard: Object):
    """match_object() returns the object when it is in the room."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        coin = setup_item(room, "silver coin")
        result = room.match_object("silver coin")
    assert result == coin


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_not_found_raises(t_init: Object, t_wizard: Object):
    """match_object() raises DoesNotExist when nothing matches the name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        with pytest.raises(Object.DoesNotExist):
            room.match_object("invisible thing")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_object_ambiguous_raises(t_init: Object, t_wizard: Object):
    """match_object() raises AmbiguousObjectError when multiple objects share a name."""
    with code.ContextManager(t_wizard, lambda msg: None):
        room = setup_room(t_wizard)
        setup_item(room, "red key")
        setup_item(room, "red key")
        with pytest.raises(exceptions.AmbiguousObjectError):
            room.match_object("red key")


# --- @exits ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_exits_no_exits(t_init: Object, t_wizard: Object):
    """@exits prints an error message when the room has no exits."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@exits")
    assert printed == ["[color red]There are no exits defined for this room.[/color red]"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_exits_lists_exits(t_init: Object, t_wizard: Object):
    """@exits lists each exit with its aliases and destination."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@dig north to The North Hall")
        printed.clear()
        parse.interpret(ctx, "@exits")
    assert printed[0] == "[color cyan]Exits defined for this room:[/color cyan]"
    assert any("north" in line and "The North Hall" in line for line in printed)


# --- @entrances ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_entrances_no_entrances(t_init: Object, t_wizard: Object):
    """@entrances prints an error message when the room has no entrances."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@entrances")
    assert printed == ["[color red]There are no entrances defined for this room.[/color red]"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_entrances_lists_entrances(t_init: Object, t_wizard: Object):
    """@entrances lists each entrance with its aliases and source room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        home = t_wizard.location
        setup_room(t_wizard, name="Far Room")
        parse.interpret(ctx, f"@tunnel south to {home.name}")
        # @tunnel added the entrance to `home`, so move back there before querying
        t_wizard.location = home
        t_wizard.save()
        context.caller.refresh_from_db()
        printed.clear()
        parse.interpret(ctx, "@entrances")
    assert printed[0] == "[color cyan]Entrances defined for this room:[/color cyan]"
    assert any("south" in line and home.name in line for line in printed)

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_basic_dig_and_tunnel(t_init: Object, t_wizard: Object):
    """dig and tunnel integration"""
    printed = []

    def _writer(msg):
        printed.append(msg)

    t_player = lookup("Player")
    with code.ContextManager(t_wizard, _writer) as ctx:
        home_location = t_wizard.location
        parse.interpret(ctx, "@dig north to Another Room")
        another_room = lookup("Another Room")
        assert printed == [
            '[color yellow]Dug an exit north to "Another Room".[/color yellow]',
        ]
        printed.clear()

        parse.interpret(ctx, "@dig north to Another Room")
        assert printed == ["[color red]There is already an exit in that direction.[/color red]"]
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_player.pk} (Player)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{t_player.pk} (Player) leaves #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_player.pk} (Player)): You arrive at #{another_room.pk} (Another Room)."
        ]
        t_player.refresh_from_db()
        assert t_player.location.name == "Another Room"
        printed.clear()

    with code.ContextManager(t_wizard, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_player.pk} (Player)): #{t_wizard.pk} (Wizard) arrives at #18 (Another Room)."
        ]
        context.caller.refresh_from_db()
        context.player.refresh_from_db()
        parse.interpret(ctx, f"@tunnel south to {home_location.name}")
        assert printed == [
            f'[color yellow]Tunnelled an exit south to "{home_location.name}".[/color yellow]',
        ]
        assert t_player.location.get_property('exits')
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go south")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_player.pk} (Player)): You leave #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{t_player.pk} (Player) leaves #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_player.pk} (Player)): You arrive at #{home_location.pk} (The Laboratory)."
        ]
        t_player.refresh_from_db()
        assert t_player.location.name == home_location.name
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        parse.interpret(ctx, "@exits")
        assert printed == [
            "[color cyan]Exits defined for this room:[/color cyan]",
            f"- [color yellow]north from The Laboratory[/color yellow] (Aliases: north) to [color green]Another Room[/color green] (#{another_room.pk})"
        ]
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        parse.interpret(ctx, "@entrances")
        assert printed == [
            "[color cyan]Entrances defined for this room:[/color cyan]",
            f"- [color yellow]south from Another Room[/color yellow] (Aliases: south) to [color green]The Laboratory[/color green] (#{home_location.pk})"
        ]
        printed.clear()
