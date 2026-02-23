import pytest

from moo.core import api, code, create, lookup, parse
from moo.core.models import Object


def setup_doors(t_wizard: Object):
    rooms = lookup("Generic Room")
    room = create("Test Room", parents=[rooms])
    doors = lookup("Generic Exit")
    door = create("wooden door", parents=[doors], location=room)
    t_wizard.location = room
    t_wizard.save()
    api.caller.refresh_from_db()
    return room, door


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_creation(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        room, door = setup_doors(t_wizard)
        parse.interpret(ctx, "@dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Dug an exit north to "Another Room".[/color yellow]']
        assert t_wizard.location == room
        assert room.has_property("exits")
        assert door in room.exits
        another_room = door.dest

        printed.clear()
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave #{room.pk} (Test Room).",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at #{another_room.pk} (Another Room)."
        ]
        api.caller.refresh_from_db()
        assert not printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_locking(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_doors(t_wizard)
        parse.interpret(ctx, "@dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Dug an exit north to "Another Room".[/color yellow]']
        printed.clear()
        parse.interpret(ctx, "lock wooden door")
        assert printed == ["The door is locked."]
        assert door.is_locked()
        printed.clear()
        parse.interpret(ctx, "unlock wooden door")
        assert printed == ["The door is unlocked."]
        assert not door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_doors(t_wizard)
        parse.interpret(ctx, "@dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Dug an exit north to "Another Room".[/color yellow]']
        printed.clear()
        parse.interpret(ctx, "open wooden door")
        assert printed == ["The door is open."]
        assert door.is_open.invoked_name == "is_open"
        assert door.is_open()
        printed.clear()
        parse.interpret(ctx, "look through wooden door")
        assert printed == ["[bright_yellow]Another Room[/bright_yellow]\n[deep_sky_blue1]There's not much to see here.[/deep_sky_blue1]"]
        printed.clear()
        parse.interpret(ctx, "close wooden door")
        assert printed == ["The door is closed."]
        assert not door.is_open()
