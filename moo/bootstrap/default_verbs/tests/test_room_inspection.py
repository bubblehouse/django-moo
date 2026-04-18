import pytest

from moo.core import code, parse
from moo.sdk import context, create, lookup
from moo.core.models import Object
from .utils import save_quietly, setup_room, setup_root_item


# --- @survey ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_room_with_exits_and_contents(t_init: Object, t_wizard: Object):
    """@survey prints exits and contents of the current room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard, name="The Vault")
        parse.interpret(ctx, "@dig north to The Annex")
        setup_root_item(room, "gold coin")
        printed.clear()
        parse.interpret(ctx, "@survey")
    assert any("The Vault" in line for line in printed)
    assert any("north" in line and "The Annex" in line for line in printed)
    assert any("gold coin" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_room_no_exits_no_contents(t_init: Object, t_wizard: Object):
    """@survey on an empty room shows only the room header."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard, name="Empty Room")
        parse.interpret(ctx, "@survey")
    assert any("Empty Room" in line for line in printed)
    assert not any("Exits:" in line for line in printed)
    assert not any("Contents:" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_by_object_id(t_init: Object, t_wizard: Object):
    """@survey #N surveys a specific room by object ID."""
    printed = []
    system = lookup(1)
    with code.ContextManager(t_wizard, printed.append) as ctx:
        other_room = create("The Observatory", parents=[system.room], location=None)
        parse.interpret(ctx, f"@survey #{other_room.pk}")
    assert any("The Observatory" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_non_room_shows_location(t_init: Object, t_wizard: Object):
    """@survey on a non-room object shows its name and location."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard)
        setup_root_item(room, "silver key")
        parse.interpret(ctx, "@survey silver key")
    assert any("silver key" in line for line in printed)
    assert any("Location" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_shows_exit_id(t_init: Object, t_wizard: Object):
    """@survey annotates each exit with its object id so agents can grant_write / lock without an @show follow-up."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard, name="The Atrium")
        parse.interpret(ctx, "@dig north to The Vestibule")
        exit_obj = lookup("north")
        printed.clear()
        parse.interpret(ctx, "@survey")
    assert any(f"(#{exit_obj.pk})" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_shows_locked_exit(t_init: Object, t_wizard: Object):
    """@survey tags a locked exit with [locked: #<key-id>]."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard, name="The Armory")
        parse.interpret(ctx, "@dig east to The Barracks")
        key = setup_root_item(room, "iron key")
        exit_obj = lookup("east")
        exit_obj.set_property("key", key.pk)
        printed.clear()
        parse.interpret(ctx, "@survey")
    assert any(f"(locked: #{key.pk})" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_room_state_dark(t_init: Object, t_wizard: Object):
    """@survey reports room state bits (dark=True) on a State: line."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        room = setup_room(t_wizard, name="The Cellar")
        room.set_property("dark", True)
        printed.clear()
        parse.interpret(ctx, "@survey")
    state_lines = [line for line in printed if "State:" in line]
    assert state_lines
    assert any("dark=True" in line for line in state_lines)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_survey_room_state_always_printed(t_init: Object, t_wizard: Object):
    """State: line is always printed, even when all room state is at defaults."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard, name="The Hall")
        printed.clear()
        parse.interpret(ctx, "@survey")
    state_lines = [line for line in printed if "State:" in line]
    assert state_lines
    assert any("dark=False" in line for line in state_lines)


# --- @rooms ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_rooms_lists_instances(t_init: Object, t_wizard: Object):
    """@rooms lists room instances and excludes the $room class itself."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda msg: None) as ctx:
        extra = create("The Greenhouse", parents=[system.room], location=None)
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "@rooms")
    messages = [str(w.message) for w in caught.list]
    output = "\n".join(messages)
    assert "The Greenhouse" in output
    assert f"#{extra.pk}" in output
    # The generic $room class itself should not appear
    assert "Generic Room" not in output


# --- @exits (targeted) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_exits_targeted_here(t_init: Object, t_wizard: Object):
    """@exits here shows exits for the current room."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@dig east to The Courtyard")
        printed.clear()
        parse.interpret(ctx, "@exits here")
    assert any("The Courtyard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_exits_targeted_by_id(t_init: Object, t_wizard: Object):
    """@exits #N shows exits for a remote room without navigating there."""
    printed = []
    system = lookup(1)
    with code.ContextManager(t_wizard, printed.append) as ctx:
        home = t_wizard.location
        # Create an unattached room, teleport into it, dig an exit, return home
        archive = create("The Archive", parents=[system.room], location=None)
        t_wizard.location = archive
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        parse.interpret(ctx, "@dig east to The Reading Room")
        t_wizard.location = home
        save_quietly(t_wizard)
        context.caller.refresh_from_db()
        printed.clear()
        parse.interpret(ctx, f"@exits #{archive.pk}")
    assert any("east" in line and "The Reading Room" in line for line in printed)


# --- look through <direction> ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_through_direction(t_init: Object, t_wizard: Object):
    """'look through <direction>' shows the destination room description."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "@dig south to The Garden")
        printed.clear()
        parse.interpret(ctx, "look through south")
    assert any("The Garden" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_through_missing_direction(t_init: Object, t_wizard: Object):
    """'look through <direction>' prints an error when no exit exists that way."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_room(t_wizard)
        parse.interpret(ctx, "look through up")
    assert any("no exit" in line.lower() for line in printed)
