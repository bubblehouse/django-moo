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


@pytest.mark.django_db
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


@pytest.mark.django_db
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


# * Can the player open every door in the game?
#   * If they can write the open property
# * Or are some doors for decoration?
#   * No
# * Are doors you can open green and ones you can’t red? Is there trash piled up in front of doors you can’t use? Did you just remove the doorknobs and call it a day?
#   * You will be told if you can't go through a door
# * Can doors be locked and unlocked?
#   * Yes
# * What tells a player a door is locked and will open, as opposed to a door that they will never open?
#   * You will be told
# * Does a player know how to unlock a door? Do they need a key? To hack a console? To solve a puzzle? To wait until a story moment passes?
#   *
# * Are there doors that can open but the player can never enter them?
#   * No
# * Where do enemies come from? Do they run in from doors? Do those doors lock afterwards?
#   * If enemies enter through doors, that doesn't necessarily change the state of the door to others
# * How does the player open a door? Do they just walk up to it and it slides open? Does it swing open? Does the player have to press a button to open it?
#   * Part of the "go" verb, which will call the "open" verb on the door
# * Do doors lock behind the player?
#   * Yes, if desired
# * What happens if there are two players? Does it only lock after both players pass through the door?
#   * Each player can go through the door independently
# * What if the level is REALLY BIG and can’t all exist at the same time? If one player stays behind, the floor might disappear from under them. What do you do?
#   * Not applicable
# * Do you stop one player from progressing any further until both are together in the same room?
#   * You could
# * Do you teleport the player that stayed behind?
#   * You could
# * What size is a door?
#   * Depends on the scenario
# * Does it have to be big enough for a player to get through?
#   * It could be
# * What about co-op players? What if player 1 is standing in the doorway – does that block player 2?
#   * Players can't normally block doorways
# * What about allies following you? How many of them need to get through the door without getting stuck?
#   * Not applicable
# * What about enemies? Do mini-bosses that are larger than a person also need to fit through the door?
#   * Not applicable
