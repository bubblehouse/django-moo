import pytest

from moo.core import api, code, create, lookup, parse
from moo.core.models import Object


def setup_doors(t_wizard: Object):
    rooms = lookup("room class")
    room = create("Test Room", parents=[rooms])
    doors = lookup("door class")
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

    with code.context(t_wizard, _writer):
        room, door = setup_doors(t_wizard)
        parse.interpret("dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Created an exit to the north to "Another Room".[/color yellow]']
        assert t_wizard.location == room
        assert room.has_property("exits")
        assert room.exits["north"]["door"] == door

        printed.clear()
        parse.interpret("go north")
        api.caller.refresh_from_db()
        assert printed == ["You go north."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_locking(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        _, door = setup_doors(t_wizard)
        parse.interpret("dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Created an exit to the north to "Another Room".[/color yellow]']
        printed.clear()
        parse.interpret("lock wooden door")
        assert printed == ["The door is locked."]
        assert door.is_locked()
        printed.clear()
        parse.interpret("unlock wooden door")
        assert printed == ["The door is unlocked."]
        assert not door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        _, door = setup_doors(t_wizard)
        parse.interpret("dig north to Another Room through wooden door")
        assert printed == ['[color yellow]Created an exit to the north to "Another Room".[/color yellow]']
        printed.clear()
        parse.interpret("open wooden door")
        assert printed == ["The door is open."]
        assert door.is_open()
        printed.clear()
        parse.interpret("look through wooden door")
        assert printed == ["[bright_yellow]Another Room[/bright_yellow]\nThere's not much to see here."]
        printed.clear()
        parse.interpret("close wooden door")
        assert printed == ["The door is closed."]
        assert not door.is_open()
