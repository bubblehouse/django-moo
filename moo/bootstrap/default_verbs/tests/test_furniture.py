import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_furniture(location, name="couch"):
    """Create a $furniture child in the given location."""
    system = lookup(1)
    return create(name, parents=[system.furniture], location=location)


# --- sit ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sit(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "sit couch")

            t_wizard.refresh_from_db()
            seated = t_wizard.get_property("seated_on")
            assert seated == couch
            assert printed == [f"You sit on {couch.title()}."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sit_already_sitting_same(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "sit couch")
            printed.clear()
            parse.interpret(ctx, "sit couch")

            assert printed == [f"You are already sitting on {couch.title()}."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sit_already_sitting_other(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            _ = setup_furniture(lab, name="couch")
            setup_furniture(lab, name="chair")

            parse.interpret(ctx, "sit couch")
            printed.clear()
            parse.interpret(ctx, "sit chair")

            assert printed == ["You're already sitting down."]


# --- stand ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_stand_no_dobj(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "sit couch")
            printed.clear()
            parse.interpret(ctx, "stand")

            t_wizard.refresh_from_db()
            seated = t_wizard.get_property("seated_on")
            assert seated is None
            assert printed == [f"You stand up from {couch.title()}."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_stand_with_dobj(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "sit couch")
            printed.clear()
            parse.interpret(ctx, "stand couch")

            t_wizard.refresh_from_db()
            seated = t_wizard.get_property("seated_on")
            assert seated is None
            assert printed == [f"You stand up from {couch.title()}."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_stand_not_sitting(t_init: Object, t_wizard: Object):
    printed = []

    with code.ContextManager(t_wizard, printed.append) as ctx:
        lab = t_wizard.location
        setup_furniture(lab)

        parse.interpret(ctx, "stand")

        assert printed == ["You aren't sitting on anything."]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_stand_wrong_furniture(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            _ = setup_furniture(lab, name="couch")
            chair = setup_furniture(lab, name="chair")

            parse.interpret(ctx, "sit couch")
            printed.clear()
            parse.interpret(ctx, "stand chair")

            assert printed == [f"You aren't sitting on {chair.title()}."]


# --- exitfunc clears seated_on ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_stand_clears_on_room_exit(t_init: Object, t_wizard: Object):
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, lambda msg: None) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "sit couch")
            t_wizard.refresh_from_db()
            assert t_wizard.get_property("seated_on") == couch

            # exitfunc is invoked asynchronously in production; call it directly here
            lab.invoke_verb("exitfunc", t_wizard)

            t_wizard.refresh_from_db()
            assert t_wizard.get_property("seated_on") is None


# --- take is blocked ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_fails(t_init: Object, t_wizard: Object):
    printed = []

    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            lab = t_wizard.location
            couch = setup_furniture(lab)

            parse.interpret(ctx, "take couch")

            couch.refresh_from_db()
            assert couch.location == lab
            assert printed == ["It's not possible to move something like this."]


# --- message verbs ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_message_verbs(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda msg: None):
        lab = t_wizard.location
        couch = setup_furniture(lab)
        title = couch.title()

        assert couch.sit_succeeded_msg() == f"You sit on {title}."
        assert couch.osit_succeeded_msg() == f"{t_wizard.name} sits on {title}."
        assert couch.sit_failed_msg() == f"You are already sitting on {title}."
        assert couch.stand_succeeded_msg() == f"You stand up from {title}."
        assert couch.ostand_succeeded_msg() == f"{t_wizard.name} stands up from {title}."
        assert couch.stand_failed_msg() == f"You aren't sitting on {title}."
