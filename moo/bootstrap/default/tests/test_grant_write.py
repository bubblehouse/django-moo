import pytest

from moo.core import code, parse
from moo.core.exceptions import AccessError
from moo.sdk import context, create, lookup
from moo.core.models import Object
from .utils import save_quietly


def setup_exit(t_wizard: Object):
    """Create a source room with a named door exit; wizard moved to source room."""
    rooms = lookup("Generic Room")
    exits = lookup("Generic Exit")
    source = create("Source Room", parents=[rooms])
    door = create("wooden door", parents=[exits], location=source)
    t_wizard.location = source
    save_quietly(t_wizard)
    context.caller.refresh_from_db()
    return source, door


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_grant_write_allows_non_wizard_to_set_property(t_init: Object, t_wizard: Object):
    """After grant_write, a non-wizard player can write to an exit they don't own."""
    printed = []

    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        source, _ = setup_exit(t_wizard)
        parse.interpret(ctx, "@dig north to Destination Room through wooden door")

    door = source.match_exit("north")
    warden = lookup("Warden")
    warden.location = source
    save_quietly(warden)

    # Warden cannot write to Wizard's exit by default
    with code.ContextManager(warden, lambda _: None):
        with pytest.raises(AccessError):
            door.set_property("key", door.pk)

    # Warden calls grant_write on the door — should grant write permission
    with code.ContextManager(warden, printed.append) as ctx:
        parse.interpret(ctx, f"grant_write #{door.pk}")

    assert any("Write access granted" in line for line in printed)

    # Now Warden can write to the door
    with code.ContextManager(warden, lambda _: None):
        door.set_property("key", door.pk)

    door.refresh_from_db()
    assert door.is_locked()
