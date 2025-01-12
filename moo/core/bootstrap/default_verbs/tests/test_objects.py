import pytest

from moo.core.models import Object
from moo.core import code, parse, lookup

@pytest.mark.django_db
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_creation(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("make a widget")
        widget = lookup('widget')
        assert widget.location == t_wizard.location
        assert printed == [
            '[color yellow]Created #15 (widget)[/color yellow]',
        ]
        printed.clear()

@pytest.mark.django_db
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_transmutation(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("make a jar from container")
        assert printed == [
            '[color yellow]Created #15 (jar)[/color yellow]',
            '[color yellow]Transmuted #15 (jar) to #2 (container class)[/color yellow]'
        ]
        printed.clear()

@pytest.mark.django_db
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_description(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("make a thingy")
        assert printed == [
            '[color yellow]Created #15 (thingy)[/color yellow]',
        ]
        printed.clear()

        parse.interpret("describe")
        parse.interpret("describe thingy")
        assert printed == [
            '[red]What do you want to describe?[/red]',
            '[red]What do you want to describe that as?[/red]',
        ]
        printed.clear()

        parse.interpret("describe thingy as 'a dusty old widget'")
        parse.interpret("look at thingy")
        assert printed == [
            "[color yellow]Description set for #15 (thingy)[/color yellow]",
            "[bright_yellow]thingy[/bright_yellow]",
            "[deep_sky_blue1]a dusty old widget[/deep_sky_blue1]"
        ]
        printed.clear()
