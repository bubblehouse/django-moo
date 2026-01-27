import pytest

from moo.core import code, parse, lookup
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
            "ConnectionError(#15 (Player)): You leave #14 (The Laboratory).",
            "ConnectionError(#3 (Wizard)): #15 (Player) leaves #14 (The Laboratory).",
            "ConnectionError(#15 (Player)): You arrive at #17 (Another Room)."
        ]
        avatar.refresh_from_db()
        assert avatar.location.name == "Another Room"
        printed.clear()

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, f"@tunnel south to {home_location.name}")
        assert printed == [
            f'[color yellow]Tunnelled an exit south to "{home_location.name}".[/color yellow]',
        ]
        printed.clear()

    with code.context(avatar, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go south")
        assert [str(x.message) for x in warnings.list] == [
            "ConnectionError(#15 (Player)): You leave #17 (Another Room).",
            "ConnectionError(#15 (Player)): You arrive at #14 (The Laboratory).",
            "ConnectionError(#3 (Wizard)): #15 (Player) arrives in #14 (The Laboratory)."
        ]
        avatar.refresh_from_db()
        assert avatar.location.name == home_location.name
        printed.clear()
