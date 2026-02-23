import pytest

from moo.core import code, create, lookup, parse
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_from_inventory(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        player = lookup("Player")
        widget = create("widget", parents=[system.thing], location=t_wizard)

        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "drop widget")
        assert [str(x.message) for x in warnings.list] == [
            f"ConnectionError(#{player.pk} (Player)): #{t_wizard.pk} (Wizard) drops widget."
        ]

        widget.refresh_from_db()
        assert widget.location == lab
        assert printed == ['You drop widget.']


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_not_in_inventory(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        widget = create("widget", parents=[system.thing], location=lab)

        parse.interpret(ctx, "drop widget")

        assert printed == ["You check your pockets, but can't find widget."]
        widget.refresh_from_db()
        assert widget.location == lab


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        system = lookup(1)
        lab = t_wizard.location
        widget = create("widget", parents=[system.thing], location=t_wizard)

        widget.moveto(lab)

        widget.refresh_from_db()
        assert widget.location == lab


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto_locked(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        system = lookup(1)
        rooms = lookup("Generic Room")
        lab = t_wizard.location
        destination = create("Locked Room", parents=[rooms], location=None)
        widget = create("widget", parents=[system.thing], location=lab)

        destination.set_property("key", ["!", widget.id])

        widget.moveto(destination)

        widget.refresh_from_db()
        assert widget.location == lab


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_message_verbs(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        system = lookup(1)
        widget = create("widget", parents=[system.thing], location=t_wizard)

        assert widget.take_succeeded_msg() == f"You take {widget.title()}."
        assert widget.take_failed_msg() == "You can't pick that up."
        assert widget.otake_failed_msg() == ""
        assert widget.drop_succeeded_msg() == f"You drop {widget.title()}."
        assert widget.drop_failed_msg() == f"You can't seem to drop {widget.title()} here."
        assert widget.odrop_succeeded_msg() == f"{t_wizard} drops {widget.title()}."
        assert widget.odrop_failed_msg() == f"{t_wizard} tries to drop {widget.title()} but fails!"
