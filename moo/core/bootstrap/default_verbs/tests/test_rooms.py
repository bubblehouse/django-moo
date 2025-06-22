import pytest

from moo.core import code, parse
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_basic_dig_and_tunnel(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        home_location = t_wizard.location
        parse.interpret("dig north to Another Room")
        assert printed == [
            '[color yellow]Created an exit to the north to "Another Room".[/color yellow]',
        ]
        printed.clear()

        parse.interpret("dig north to Another Room")
        assert printed == ["[color red]There is already an exit in that direction.[/color red]"]
        printed.clear()

        parse.interpret("go north")
        t_wizard.refresh_from_db()
        assert t_wizard.location.name == "Another Room"
        printed.clear()

        parse.interpret(f"tunnel south to {home_location.name}")
        assert printed == [
            f'[color yellow]Created an exit to the south to "{home_location.name}".[/color yellow]',
        ]
        printed.clear()

        parse.interpret("go south")
        t_wizard.refresh_from_db()
        assert t_wizard.location.name == home_location.name
        printed.clear()
