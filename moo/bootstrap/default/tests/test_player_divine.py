import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_location_random_rooms(t_init: Object, t_wizard: Object):
    """@divine location without `of` returns random rooms from the world."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@divine location")
    joined = "\n".join(printed)
    assert "Impressions surface" in joined


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_child_of_class(t_init: Object, t_wizard: Object):
    """@divine child of $thing returns up to three descendants of $thing."""
    system = lookup(1)
    room = t_wizard.location
    create("test widget alpha", parents=[system.thing], location=room)
    create("test widget beta", parents=[system.thing], location=room)
    create("test widget gamma", parents=[system.thing], location=room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@divine child of $thing")
    joined = "\n".join(printed)
    assert "Shapes coalesce" in joined
    assert "#" in joined


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_child_of_unknown_class(t_init: Object, t_wizard: Object):
    """@divine child of <bogus> prints the themed not-found message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@divine child of $nonexistent")
    assert any("cannot find a class" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_location_of_object_in_room(t_init: Object, t_wizard: Object):
    """@divine location of #N walks directly to the containing room."""
    system = lookup(1)
    room = t_wizard.location
    thing = create("cloudy glass vial", parents=[system.thing], location=room)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, f"@divine location of #{thing.pk}")
    joined = "\n".join(printed)
    assert "threads tighten" in joined
    assert f"#{room.pk}" in joined


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_location_of_object_in_container(t_init: Object, t_wizard: Object):
    """@divine location of <item> walks up through a container to the room."""
    system = lookup(1)
    room = t_wizard.location
    box = create("tarnished copper box", parents=[system.container], location=room)
    item = create("brass trinket", parents=[system.thing], location=box)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, f"@divine location of #{item.pk}")
    joined = "\n".join(printed)
    assert "threads tighten" in joined
    assert f"#{room.pk}" in joined


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_location_of_orphan(t_init: Object, t_wizard: Object):
    """@divine location of an object with no enclosing room reports failure."""
    system = lookup(1)
    orphan = create("drifting ember", parents=[system.thing])

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, f"@divine location of #{orphan.pk}")
    assert any("outside any room" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_location_of_unknown(t_init: Object, t_wizard: Object):
    """@divine location of <bogus name> prints the themed not-found message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@divine location of $phantom_object_xyz")
    assert any("cannot grasp" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_divine_unknown_subject(t_init: Object, t_wizard: Object):
    """@divine <gibberish> prints 'no answer'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@divine fortune")
    assert any("no answer" in line for line in printed)
