import pytest

from moo.core import code, parse
from moo.sdk import context, create, lookup
from moo.core.models import Object
from .utils import save_quietly, setup_room, setup_root_item

# --- look (player command) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_no_args_shows_current_room(t_init: Object, t_wizard: Object):
    """'look' with no arguments shows the current room's look_self."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        parse.interpret(ctx, "look")
    assert f"[bright_yellow]{room.name}[/bright_yellow]" in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_at_named_object(t_init: Object, t_wizard: Object):
    """'look <name>' shows the description of the named object in the room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        coin = setup_root_item(room, "gold coin")
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


# --- huh / huh2 ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_huh_unrecognised_command(t_init: Object, t_wizard: Object):
    """An unrecognised command triggers huh2, which tells the player 'Huh?'."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "xyzzy")
    messages = [str(w.message) for w in caught.list]
    assert any("Huh?" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_huh2_exit_match_by_name(t_init: Object, t_wizard: Object):
    """huh2 invokes an exit when the verb matches the exit's alias."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        # Create an exit whose alias is a non-cardinal single word
        parse.interpret(ctx, "@dig portal to Portal Room")
        context.caller.refresh_from_db()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "portal")
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in caught.list]
    assert any("Portal Room" in m for m in messages)
    assert t_wizard.location.name == "Portal Room"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_huh2_msg_setter_sets_property(t_init: Object, t_wizard: Object):
    """huh2 sets a _msg property when @<name> <obj> is <value> is typed."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = setup_root_item(t_wizard.location, "widget")
        widget.set_property("foobar_msg", "original")
        parse.interpret(ctx, "@foobar widget is Hello world")
        widget.refresh_from_db()
    assert widget.get_property("foobar_msg") == "Hello world"
    assert "Message 'foobar_msg' set." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_huh2_msg_setter_unknown_property_says_huh(t_init: Object, t_wizard: Object):
    """huh2 falls through to 'Huh?' when the @<name>_msg property doesn't exist."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        setup_root_item(t_wizard.location, "widget")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "@frobnitz widget is value")
    messages = [str(w.message) for w in caught.list]
    assert any("Huh?" in m for m in messages)


# --- cardinals ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_cardinal_no_exit_says_cant_go(t_init: Object, t_wizard: Object):
    """Typing a cardinal direction with no matching exit tells the player they can't go that way."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        setup_room(t_wizard)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "north")
    messages = [str(w.message) for w in caught.list]
    assert any("You can't go that way." in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_cardinal_moves_player(t_init: Object, t_wizard: Object):
    """Typing a cardinal direction with a matching exit moves the player."""
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@dig north to Northern Hall")
        context.caller.refresh_from_db()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "north")
        t_wizard.refresh_from_db()
    messages = [str(w.message) for w in caught.list]
    assert any("Northern Hall" in m for m in messages)
    assert t_wizard.location.name == "Northern Hall"


# --- explain ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_explain_verb_takes_no_dobj(t_init: Object, t_wizard: Object):
    """explain tells the player a verb doesn't take a direct object when one is given."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        # 'news' has dspec=none; giving it a dobj triggers explain
        parse.interpret(ctx, "news ball")
    assert any("doesn't take a direct object" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_explain_verb_requires_dobj(t_init: Object, t_wizard: Object):
    """explain tells the player a verb requires a direct object when none is given."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        # '@dig' has dspec=any; omitting the dobj triggers explain
        parse.interpret(ctx, "@dig")
    assert any("requires a direct object" in line for line in printed)


# --- @exits ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_exits_no_exits(t_init: Object, t_wizard: Object):
    """@exits prints an error message when the room has no exits."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@exits")
    assert printed == ["[red]There are no exits defined for this room.[/red]"]


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
    assert printed[0] == "[cyan]Exits defined for this room:[/cyan]"
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
    assert printed == ["[red]There are no entrances defined for this room.[/red]"]


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
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        printed.clear()
        parse.interpret(ctx, "@entrances")
    assert printed[0] == "[cyan]Entrances defined for this room:[/cyan]"
    assert any("south" in line and home.name in line for line in printed)


# --- @dig / @tunnel integration ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_basic_dig_and_tunnel(t_init: Object, t_wizard: Object):
    """dig and tunnel integration"""
    printed = []

    def _writer(msg):
        printed.append(msg)

    def _msgs(caught, *objs):
        """Filter ConnectionError warnings to only those sent to the given objects."""
        prefixes = tuple(f"ConnectionError(#{obj.pk} " for obj in objs)
        return [str(w.message) for w in caught.list if str(w.message).startswith(prefixes)]

    t_player = lookup("Player")
    with code.ContextManager(t_wizard, _writer) as ctx:
        home_location = t_wizard.location
        lab_desc = home_location.description()
        parse.interpret(ctx, "@dig north to Another Room")
        another_room = lookup("Another Room")
        assert printed == [
            '[yellow]Dug an exit north to "Another Room".[/yellow]',
        ]
        printed.clear()

        parse.interpret(ctx, "@dig north to Another Room")
        assert printed == ["[red]There is already an exit in that direction.[/red]"]
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "go north")
        assert _msgs(caught, t_player, t_wizard) == [
            f"ConnectionError(#{t_player.pk} (Player)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{t_player.pk} (Player) leaves #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_player.pk} (Player)): [bright_yellow]Another Room[/bright_yellow]",
            f"ConnectionError(#{t_player.pk} (Player)): [deep_sky_blue1]There's not much to see here.[/deep_sky_blue1]",
            f"ConnectionError(#{t_player.pk} (Player)): You arrive at #{another_room.pk} (Another Room).",
        ]
        t_player.refresh_from_db()
        assert t_player.location.name == "Another Room"
        printed.clear()

    with code.ContextManager(t_wizard, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "go north")
        assert _msgs(caught, t_player, t_wizard) == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): [bright_yellow]Another Room[/bright_yellow]",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): [deep_sky_blue1]There's not much to see here.[/deep_sky_blue1]",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): {t_player.name} is here.",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_player.pk} (Player)): #{t_wizard.pk} (Wizard) arrives at #{another_room.pk} (Another Room).",
        ]
        context.caller.refresh_from_db()
        context.player.refresh_from_db()
        parse.interpret(ctx, f"@tunnel south to {home_location.name}")
        assert printed == [
            f'[yellow]Tunnelled an exit south to "{home_location.name}".[/yellow]',
        ]
        assert t_player.location.get_property("exits")
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "go south")
        assert _msgs(caught, t_player, t_wizard) == [
            f"ConnectionError(#{t_player.pk} (Player)): You leave #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{t_player.pk} (Player) leaves #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_player.pk} (Player)): [bright_yellow]The Laboratory[/bright_yellow]",
            f"ConnectionError(#{t_player.pk} (Player)): {lab_desc}",
            f"ConnectionError(#{t_player.pk} (Player)): You arrive at #{home_location.pk} (The Laboratory).",
        ]
        t_player.refresh_from_db()
        assert t_player.location.name == home_location.name
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        parse.interpret(ctx, "@exits")
        assert printed == [
            "[cyan]Exits defined for this room:[/cyan]",
            f"- [yellow]north from The Laboratory[/yellow] (Aliases: north) to [green]Another Room[/green] (#{another_room.pk})",
        ]
        printed.clear()

    with code.ContextManager(t_player, _writer) as ctx:
        parse.interpret(ctx, "@entrances")
        assert printed == [
            "[cyan]Entrances defined for this room:[/cyan]",
            f"- [yellow]south from Another Room[/yellow] (Aliases: south) to [green]The Laboratory[/green] (#{home_location.pk})",
        ]
        printed.clear()
