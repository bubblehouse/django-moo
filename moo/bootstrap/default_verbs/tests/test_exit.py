import pytest

from moo.core import api, code, create, lookup, parse
from moo.core.models import Object


def setup_exit(t_wizard: Object):
    """Create a source room with a named door exit; wizard moved to source room."""
    rooms = lookup("Generic Room")
    exits = lookup("Generic Exit")
    source = create("Source Room", parents=[rooms])
    door = create("wooden door", parents=[exits], location=source)
    t_wizard.location = source
    t_wizard.save()
    api.caller.refresh_from_db()
    return source, door


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_open_default(t_init: Object, t_wizard: Object):
    """A freshly dug exit is not open by default."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        assert not door.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_locked_default(t_init: Object, t_wizard: Object):
    """A freshly dug exit is not locked by default."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        assert not door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_exit(t_init: Object, t_wizard: Object):
    """Opening an exit marks it as open."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        printed.clear()
        parse.interpret(ctx, "open wooden door")
        assert printed == ["The door is open."]
        assert door.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_already_open(t_init: Object, t_wizard: Object):
    """Opening an already open exit prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        parse.interpret(ctx, "open wooden door")
        printed.clear()
        parse.interpret(ctx, "open wooden door")
        assert printed == ["The door is already open."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_locked_exit(t_init: Object, t_wizard: Object):
    """Opening a locked exit prints a locked message and leaves it closed."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        parse.interpret(ctx, "lock wooden door")
        printed.clear()
        parse.interpret(ctx, "open wooden door")
        assert printed == ["The door is locked."]
        assert not door.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_close_exit(t_init: Object, t_wizard: Object):
    """Closing an open exit marks it as closed."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        parse.interpret(ctx, "open wooden door")
        printed.clear()
        parse.interpret(ctx, "close wooden door")
        assert printed == ["The door is closed."]
        assert not door.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_close_already_closed(t_init: Object, t_wizard: Object):
    """Closing an already closed exit prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        printed.clear()
        parse.interpret(ctx, "close wooden door")
        assert printed == ["The door is already closed."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_close_door_with_autolock(t_init: Object, t_wizard: Object):
    """Closing a door with autolock=True automatically locks it."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        door.set_property("autolock", True)
        parse.interpret(ctx, "open wooden door")
        printed.clear()
        parse.interpret(ctx, "close wooden door")
        assert printed == ["The door is closed."]
        assert door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_exit(t_init: Object, t_wizard: Object):
    """Locking an exit marks it as locked."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        printed.clear()
        parse.interpret(ctx, "lock wooden door")
        assert printed == ["The door is locked."]
        assert door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_already_locked(t_init: Object, t_wizard: Object):
    """Locking an already locked exit prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        parse.interpret(ctx, "lock wooden door")
        printed.clear()
        parse.interpret(ctx, "lock wooden door")
        assert printed == ["The door is already locked."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unlock_exit(t_init: Object, t_wizard: Object):
    """Unlocking a locked exit clears the locked property."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        _, door = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        parse.interpret(ctx, "lock wooden door")
        printed.clear()
        parse.interpret(ctx, "unlock wooden door")
        assert printed == ["The door is unlocked."]
        assert not door.is_locked()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unlock_not_locked(t_init: Object, t_wizard: Object):
    """Unlocking a non-locked exit prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        printed.clear()
        parse.interpret(ctx, "unlock wooden door")
        assert printed == ["The door is not locked."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_door_not_in_exits(t_init: Object, t_wizard: Object):
    """Opening a door not registered in the room's exits list prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        # setup_exit places the door in the room but does NOT @dig,
        # so match_exit won't find it in the room's exits property
        setup_exit(t_wizard)
        parse.interpret(ctx, "open wooden door")
        assert printed == ["There is no door called wooden door here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_door_not_in_exits(t_init: Object, t_wizard: Object):
    """Locking a door not registered in the room's exits list prints an error."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "lock wooden door")
        assert printed == ["There is no door called wooden door here."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_through_exit(t_init: Object, t_wizard: Object):
    """Looking through an exit shows the destination room's description."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        printed.clear()
        parse.interpret(ctx, "look through wooden door")
        assert printed == [
            "[bright_yellow]Destination Room[/bright_yellow]\n[deep_sky_blue1]There's not much to see here.[/deep_sky_blue1]"
        ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_through_exit(t_init: Object, t_wizard: Object):
    """Moving through an exit relocates the player to the destination room."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        source, _ = setup_exit(t_wizard)
        player = lookup("Player")
        player.location = source
        player.save()
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        dest = lookup("Destination Room")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "go north")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave {source}.",
            f"ConnectionError(#{player.pk} (Player)): {t_wizard} leaves {source}.",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at {dest}.",
        ]
        api.caller.refresh_from_db()
        assert api.caller.location == dest


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_move_nonexistent_direction(t_init: Object, t_wizard: Object):
    """Going in a direction with no exit prints a help message."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "go nowhere")
        assert printed == ["Go where?"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_message_verbs(t_init: Object, t_wizard: Object):
    """All exit message verbs return properly substituted strings."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        source, _ = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        dest = lookup("Destination Room")
        door = source.match_exit("north")
        assert door.leave_msg() == f"You leave {source}."
        assert door.arrive_msg() == f"You arrive at {dest}."
        assert door.oleave_msg() == f"{t_wizard} leaves {source}."
        assert door.oarrive_msg() == f"{t_wizard} arrives at {dest}."
        assert door.nogo_msg() == "You can't go that way."
        assert door.onogo_msg() == f"{t_wizard} can't go that way."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_invoke_moves_player(t_init: Object, t_wizard: Object):
    """Directly invoking an exit moves the player to the destination."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        source, _ = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")
        dest = lookup("Destination Room")
        player = lookup("Player")
        player.location = dest
        player.save()
        door = source.match_exit("north")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            door.invoke(t_wizard)
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave {source}.",
            f"ConnectionError(#{t_wizard.pk} (Wizard)): You arrive at {dest}.",
            f"ConnectionError(#{player.pk} (Player)): {t_wizard} arrives at {dest}.",
        ]
        api.caller.refresh_from_db()
        assert api.caller.location == dest
