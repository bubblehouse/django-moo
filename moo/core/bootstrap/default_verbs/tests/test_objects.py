import pytest

from moo.core.models import Object
from moo.core import code, parse, lookup

@pytest.mark.django_db
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_creation_and_description(t_init: Object, t_wizard: Object):
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

        parse.interpret("make a jar from container")
        assert printed == [
            '[color yellow]Created #16 (jar)[/color yellow]',
            '[color yellow]Transmuted #16 (jar) to #2 (container class)[/color yellow]'
        ]
        printed.clear()

        parse.interpret("describe jar as 'a dusty old container'")
        parse.interpret("look at jar")
        assert printed == [
            "Description set for #16 (jar)",
            "[bright_yellow]jar[/bright_yellow]",
            "[deep_sky_blue1]a dusty old container[/deep_sky_blue1]"
        ]
        printed.clear()
