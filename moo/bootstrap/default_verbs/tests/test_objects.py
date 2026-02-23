import pytest

from moo.core import code, lookup, parse
from moo.core.models import Object, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_creation(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "make a widget")
        widget = lookup("widget")
        assert widget.location == t_wizard.location
        assert printed == [
            f"[color yellow]Created #{widget.id} (widget)[/color yellow]",
        ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_transmutation(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "make a jar from Generic Container")
        jar = lookup("jar")
        container = lookup("Generic Container")
        assert printed == [
            f"[color yellow]Created #{jar.id} (jar)[/color yellow]",
            f"[color yellow]Transmuted #{jar.id} (jar) to #{container.id} (Generic Container)[/color yellow]",
        ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_description(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "make a thingy from Root Class")
        thingy = lookup("thingy")
        root = lookup("Root Class")
        assert list(thingy.parents.all()) == [root]
        assert printed == [
            f"[color yellow]Created #{thingy.id} (thingy)[/color yellow]",
            f"[color yellow]Transmuted #{thingy.id} (thingy) to #4 (Root Class)[/color yellow]",
        ]
        printed.clear()

        # parse.interpret(ctx, "@describe thingy")
        # assert printed == [
        #     "[red]What do you want to describe that as?[/red]",
        # ]
        # printed.clear()

        parse.interpret(ctx, "@describe thingy as 'a dusty old widget'")
        parse.interpret(ctx, "look at thingy")
        print(printed)
        assert printed == [
            f"[color yellow]Description set for #{thingy.id} (thingy)[/color yellow]",
            "[bright_yellow]thingy[/bright_yellow]\n[deep_sky_blue1]a dusty old widget[/deep_sky_blue1]",
        ]
