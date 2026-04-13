import pytest

from moo.core import code, parse
from moo.core.exceptions import AccessError
from moo.sdk import create, lookup
from moo.core.models import Object
from .utils import save_quietly


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tailor_grant_write_allows_property_edit(t_init: Object, t_wizard: Object):
    """After grant_write, Tailor can set a property on an object it doesn't own."""
    printed = []
    system = lookup(1)

    with code.ContextManager(t_wizard, lambda _: None):
        thing = create("embroidered waistcoat", parents=[system.thing], location=t_wizard.location)

    tailor = lookup("Tailor")
    tailor.location = t_wizard.location
    save_quietly(tailor)

    with code.ContextManager(tailor, lambda _: None):
        with pytest.raises(AccessError):
            thing.set_property("take_succeeded_msg", "You don the {title} with quiet pride.")

    with code.ContextManager(tailor, printed.append) as ctx:
        parse.interpret(ctx, f"grant_write #{thing.pk}")

    assert any("Write access granted" in line for line in printed)

    with code.ContextManager(tailor, lambda _: None):
        thing.set_property("take_succeeded_msg", "You don the {title} with quiet pride.")

    thing.refresh_from_db()
    assert thing.get_property("take_succeeded_msg").startswith("You don")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tailor_grant_move_allows_relocation(t_init: Object, t_wizard: Object):
    """After grant_move, Tailor can change an object's location (take/drop)."""
    printed = []
    system = lookup(1)

    with code.ContextManager(t_wizard, lambda _: None):
        thing = create("silver thimble", parents=[system.thing], location=t_wizard.location)

    tailor = lookup("Tailor")
    tailor.location = t_wizard.location
    save_quietly(tailor)

    with code.ContextManager(tailor, lambda _: None):
        with pytest.raises(AccessError):
            thing.location = tailor
            save_quietly(thing)

    thing.refresh_from_db()

    with code.ContextManager(tailor, printed.append) as ctx:
        parse.interpret(ctx, f"grant_write #{thing.pk}")
        parse.interpret(ctx, f"grant_move #{thing.pk}")

    assert any("Write access granted" in line for line in printed)
    assert any("Move access granted" in line for line in printed)

    with code.ContextManager(tailor, lambda _: None):
        thing.location = tailor
        save_quietly(thing)

    thing.refresh_from_db()
    assert thing.location_id == tailor.pk
