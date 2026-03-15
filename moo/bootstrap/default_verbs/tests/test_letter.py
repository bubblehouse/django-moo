import pytest

from moo.core import code, exceptions, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_letter(wizard: Object, text: str = "", name: str = "sealed letter") -> Object:
    system = lookup(1)
    letter = create(name, parents=[system.letter], location=wizard.location)
    letter.set_property("text", text)
    return letter


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_burn_readable(t_init: Object, t_wizard: Object):
    """A readable letter (no lock) is destroyed when burned."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        letter = setup_letter(t_wizard, name="sealed letter")
        name = letter.title()
        with pytest.warns(RuntimeWarning) as warning_list:
            parse.interpret(ctx, "burn sealed letter")

    messages = [str(w.message) for w in warning_list]
    assert any(f"{name} burns with a smokeless flame, and leaves no ash." in m for m in messages)
    with pytest.raises(exceptions.NoSuchObjectError):
        lookup("sealed letter")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_burn_unreadable(t_init: Object, t_wizard: Object):
    """A letter locked for someone else cannot be burned."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        letter = setup_letter(t_wizard, name="sealed letter")
        name = letter.title()
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        letter.set_property("read_key", key.id)
        with pytest.warns(RuntimeWarning) as warning_list:
            parse.interpret(ctx, "burn sealed letter")

    messages = [str(w.message) for w in warning_list]
    assert any(f"{name} might be damp, in any case it won't burn." in m for m in messages)
    letter.refresh_from_db()
    assert letter.location == t_wizard.location


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_letter_inherits_read(t_init: Object, t_wizard: Object):
    """$letter inherits the read verb from $note."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        setup_letter(t_wizard, text="Dear Wizard,\nHow are you?", name="sealed letter")
        parse.interpret(ctx, "read sealed letter")

    assert printed == ["Dear Wizard,\nHow are you?"]
