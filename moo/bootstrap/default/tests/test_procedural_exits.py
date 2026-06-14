"""Tests for procedural / lattice exits (spec 200, item D)."""

import pytest

from moo.core import code, create, parse
from moo.core.models import Object
from moo.sdk import lookup, guaranteed_moveto

# An override that computes an exit to the room stored in `procedural_dest`,
# returning a standard $exit object so movement reuses the normal move path.
_PROCEDURAL = """
from moo.sdk import create, lookup
dest = this.get_property('procedural_dest')
ex = create(args[0], parents=[lookup('Generic Exit')])
ex.set_property('source', this)
ex.set_property('dest', dest)
return ex
"""


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_default_has_no_procedural_exit(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        a = create("Lonely Room", parents=[lookup("Generic Room")])
        a.set_property("exits", [])
        guaranteed_moveto(t_wizard, a)
        parse.interpret(ctx, "north")  # no stored or computed exit
        t_wizard.refresh_from_db()
        assert t_wizard.location == a  # didn't move


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_procedural_exit_drives_standard_move(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        a = create("Grid A", parents=[lookup("Generic Room")])
        b = create("Grid B", parents=[lookup("Generic Room")])
        a.set_property("exits", [])
        a.set_property("procedural_dest", b)
        a.add_verb("procedural_exit", code=_PROCEDURAL, direct_object="any", replace=True)
        guaranteed_moveto(t_wizard, a)
        # No stored exit matches; the computed exit routes through exit.invoke -> move.
        assert a.match_exit("north") is None
        parse.interpret(ctx, "north")
        t_wizard.refresh_from_db()
        assert t_wizard.location == b


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_procedural_exit_via_go_verb(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        a = create("Tile A", parents=[lookup("Generic Room")])
        b = create("Tile B", parents=[lookup("Generic Room")])
        a.set_property("exits", [])
        a.set_property("procedural_dest", b)
        a.add_verb("procedural_exit", code=_PROCEDURAL, direct_object="any", replace=True)
        guaranteed_moveto(t_wizard, a)
        parse.interpret(ctx, "go east")
        t_wizard.refresh_from_db()
        assert t_wizard.location == b
