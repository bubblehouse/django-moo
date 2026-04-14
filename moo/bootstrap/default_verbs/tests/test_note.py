import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_note(wizard: Object, text: str = "", name: str = "scrap of paper") -> Object:
    system = lookup(1)
    note = create(name, parents=[system.note], location=wizard.location)
    note.set_property("text", text)
    return note


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_readable_by_no_key(t_init: Object, t_wizard: Object):
    """A note with no read_key is always readable."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        note = setup_note(t_wizard)
        assert note.is_readable_by(t_wizard) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_no_lock(t_init: Object, t_wizard: Object):
    """Reading an unlocked note prints its text."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        _note = setup_note(t_wizard, text="Hello, world!")
        parse.interpret(ctx, "read scrap of paper")
        assert printed == ['"Hello, world!"']


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_locked_without_key(t_init: Object, t_wizard: Object):
    """Reading a locked note when the player doesn't hold the key prints nothing."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        note = setup_note(t_wizard, text="Secret text.")
        key = create("brass key", parents=[system.thing], location=lab)
        note.set_property("read_key", key.id)
        parse.interpret(ctx, "read scrap of paper")
        assert not printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_locked_with_key_in_inventory(t_init: Object, t_wizard: Object):
    """Reading a locked note while holding the key prints its text."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        note = setup_note(t_wizard, text="Secret text.")
        key = create("brass key", parents=[system.thing], location=t_wizard)
        note.set_property("read_key", key.id)
        parse.interpret(ctx, "read scrap of paper")
        assert printed == ['"Secret text."']


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_as_owner(t_init: Object, t_wizard: Object):
    """The owner can erase a note's text."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        note = setup_note(t_wizard, text="Some content.")
        parse.interpret(ctx, "erase scrap of paper")
        note.refresh_from_db()
        assert note.get_property("text") == ""


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_for_read(t_init: Object, t_wizard: Object):
    """@lock_for_read with a simple #N keyexp stores the key ID."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        note = setup_note(t_wizard)
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, f"@lock_for_read scrap of paper with #{key.id}")
        assert note.get_property("read_key") == key.id


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_for_read_negation(t_init: Object, t_wizard: Object):
    """A negated keyexp (!#N) is stored as a list."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        note = setup_note(t_wizard)
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, f'@lock_for_read scrap of paper with "!#{key.id}"')
        assert note.get_property("read_key") == ["!", key.id]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_for_read_or(t_init: Object, t_wizard: Object):
    """An OR keyexp (#N || #M) is stored as a list."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        note = setup_note(t_wizard)
        key1 = create("brass key", parents=[system.thing], location=t_wizard.location)
        key2 = create("silver key", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, f'@lock_for_read scrap of paper with "#{key1.id} || #{key2.id}"')
        assert note.get_property("read_key") == ["||", key1.id, key2.id]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unlock_for_read(t_init: Object, t_wizard: Object):
    """@unlock_for_read clears the read_key."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        note = setup_note(t_wizard)
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        note.set_property("read_key", key.id)
        parse.interpret(ctx, "@unlock_for_read scrap of paper")
        assert note.get_property("read_key") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_callback_sets_text(t_init: Object, t_wizard: Object):
    """edit_callback stores the new text on the note."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        note = setup_note(t_wizard, text="")
        note.edit_callback("hello world")
        note.refresh_from_db()
        assert note.get_property("text") == "hello world"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_no_permission(t_init: Object, t_wizard: Object):
    """@edit prints a denial when the player does not own the note."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        player = lookup("Player")
        system = lookup(1)
        note = create("scrap of paper", parents=[system.note], location=t_wizard.location)
        note.set_property("text", "")
        note.owner = player
        note.save()
        parse.interpret(ctx, "@edit scrap of paper")
        assert printed == ["You don't have permission to edit this note."]
