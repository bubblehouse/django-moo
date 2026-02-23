import pytest

from moo.core import api, code, parse, lookup
from moo.core.models import Object, Player


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_basic_dig_and_tunnel(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    t_player = lookup("Player")
    with code.context(t_wizard, _writer) as ctx:
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

    with code.context(t_player, _writer) as ctx:
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

    with code.context(t_wizard, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_player.pk} (Player)): #{t_wizard.pk} (Wizard) arrives at #18 (Another Room)."
        ]
        api.caller.refresh_from_db()
        api.player.refresh_from_db()
        parse.interpret(ctx, f"@tunnel south to {home_location.name}")
        assert printed == [
            f'[color yellow]Tunnelled an exit south to "{home_location.name}".[/color yellow]',
        ]
        assert t_player.location.get_property('exits')
        printed.clear()

    with code.context(t_player, _writer) as ctx:
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

    with code.context(t_player, _writer) as ctx:
        parse.interpret(ctx, "@exits")
        assert printed == [
            "[color cyan]Exits defined for this room:[/color cyan]",
            f"- [color yellow]north from The Laboratory[/color yellow] (Aliases: north) to [color green]Another Room[/color green] (#{another_room.pk})"
        ]
        printed.clear()

    with code.context(t_player, _writer) as ctx:
        parse.interpret(ctx, "@entrances")
        assert printed == [
            "[color cyan]Entrances defined for this room:[/color cyan]",
            f"- [color yellow]south from Another Room[/color yellow] (Aliases: south) to [color green]The Laboratory[/color green] (#{home_location.pk})"
        ]
        printed.clear()
