import pytest

from moo.core import api, code, parse, lookup
from moo.core.models import Object, Player


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_basic_dig_and_tunnel(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    avatar = lookup("Player")
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

    with code.context(avatar, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{avatar.pk} (Player)): You leave #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{avatar.pk} (Player) leaves #{home_location.pk} (The Laboratory).",
            f"ConnectionError(#{avatar.pk} (Player)): You arrive at #{another_room.pk} (Another Room)."
        ]
        avatar.refresh_from_db()
        assert avatar.location.name == "Another Room"
        printed.clear()

    with code.context(t_wizard, _writer) as ctx:
        t_wizard.location = avatar.location
        t_wizard.save()
        api.caller.refresh_from_db()
        parse.interpret(ctx, f"@tunnel south to {home_location.name}")
        assert printed == [
            f'[color yellow]Tunnelled an exit south to "{home_location.name}".[/color yellow]',
        ]
        printed.clear()

    with code.context(avatar, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go south")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{avatar.pk} (Player)): You leave #{another_room.pk} (Another Room).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): #{avatar.pk} (Player) leaves #{another_room.pk} (Another Room).",
            f"ConnectionError(#{avatar.pk} (Player)): You arrive at #{home_location.pk} (The Laboratory)."
        ]
        avatar.refresh_from_db()
        assert avatar.location.name == home_location.name
        printed.clear()

    with code.context(avatar, _writer) as ctx:
        parse.interpret(ctx, "@exits")
        assert printed == [
            "[color cyan]Exits defined for this room:[/color cyan]",
            f"- [color yellow]north from The Laboratory[/color yellow] (Aliases: north) to [color green]Another Room[/color green] (#{another_room.pk})"
        ]
        printed.clear()
