import pytest

from moo.core.models import Object
from moo.core import code, parse

@pytest.mark.django_db
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_creation_and_description(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("make a widget")
        assert printed == [
            '[color yellow]Created #15 (a widget)[/color yellow]',
        ]
        printed.clear()

        parse.interpret("make a jar from container")
        assert printed == [
            '[color yellow]Created #16 (a jar)[/color yellow]',
            '[color yellow]Transmuted #16 (a jar) to #2 (container class)[/color yellow]'
        ]
        printed.clear()
