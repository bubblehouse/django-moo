import pytest

from moo.core import code, parse
from moo.core.models import Object

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_say(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
            parse.interpret(ctx, "say Hello, world!")
        assert [str(x.message) for x in warnings.list] == [
            "ConnectionError(#3 (Wizard)): You: Hello, world!"
        ]
