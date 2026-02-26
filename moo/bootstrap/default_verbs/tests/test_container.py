import pytest

from moo.core import code, create, lookup, parse
from moo.core.models import Object


def setup_container(t_wizard: Object):
    containers = lookup("Generic Container")
    box = create("wooden box", parents=[containers], location=t_wizard.location)
    return box


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_open_default(t_init: Object, t_wizard: Object):
    """Container starts closed by default."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        box = setup_container(t_wizard)
        assert not box.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        box = setup_container(t_wizard)
        parse.interpret(ctx, "open wooden box")
        box.refresh_from_db()
        assert printed == ["You open the container."]
        assert box.is_open()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_open_already_open(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        box = setup_container(t_wizard)
        parse.interpret(ctx, "open wooden box")
        printed.clear()
        parse.interpret(ctx, "open wooden box")
        assert printed == ["Container is already open."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_close_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        box = setup_container(t_wizard)
        assert not box.is_open()
        parse.interpret(ctx, "open wooden box")
        assert box.is_open()
        printed.clear()
        parse.interpret(ctx, "close wooden box")
        box.refresh_from_db()
        assert not box.is_open()
        assert printed == ["You close the container."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_close_already_closed(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        box = setup_container(t_wizard)
        parse.interpret(ctx, "close wooden box")
        assert printed == ["Container is already closed."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_empty(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        box = setup_container(t_wizard)
        box.tell_contents()
        assert printed == ["It is empty."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_with_items(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=box)
        box.tell_contents()
        assert printed == ["Contents:", f"  {tobacco.title()}"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_put_in_open_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "open wooden box")
        printed.clear()
        parse.interpret(ctx, "put tobacco in wooden box")
        tobacco.refresh_from_db()
        assert tobacco.location == box
        assert printed == ["You placed tobacco in wooden box"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_put_in_closed_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "put tobacco in wooden box")
        tobacco.refresh_from_db()
        assert tobacco.location != box
        assert f"{box.title()} is closed." in printed


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_from_open_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=box)
        parse.interpret(ctx, "open wooden box")
        printed.clear()
        parse.interpret(ctx, "take tobacco from wooden box")
        tobacco.refresh_from_db()
        assert tobacco.location == t_wizard
        assert printed == ["You took tobacco from wooden box"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_from_closed_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=box)
        parse.interpret(ctx, "take tobacco from wooden box")
        tobacco.refresh_from_db()
        assert tobacco.location == box
        assert printed == [f"{box.title()} is closed."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_item_not_in_container(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        tobacco = create("tobacco", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "open wooden box")
        printed.clear()
        parse.interpret(ctx, "take tobacco from wooden box")
        assert printed == ["tobacco is not in wooden box."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_openable_by_no_key(t_init: Object, t_wizard: Object):
    """Container with no lock key is always openable."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        box = setup_container(t_wizard)
        assert box.is_openable_by(t_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lock_for_open(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "lock_for_open wooden box with brass key")
        assert box.get_property("open_key") == key


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_unlock_for_open(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        box = setup_container(t_wizard)
        key = create("brass key", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "lock_for_open wooden box with brass key")
        parse.interpret(ctx, "unlock_for_open wooden box")
        assert box.get_property("open_key") is None
