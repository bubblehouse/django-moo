import pytest

from termiverse.core.models.object import Object
from termiverse.tests import *  # pylint: disable=wildcard-import
from .. import code

@pytest.mark.django_db
def test_eval_simple_command(t_init: Object, t_wizard: Object):  # pylint: disable=redefined-outer-name
    def _writer(msg):
        raise RuntimeError("print was called unexpectedly")
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("dir()", {}, globals)
        assert result == []

@pytest.mark.django_db
def test_trivial_printing(t_init: Object, t_wizard: Object):  # pylint: disable=redefined-outer-name
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("print('test')", {}, globals)
        assert result is None
        assert printed == ['test']

@pytest.mark.django_db
def test_printing_imported_caller(t_init: Object, t_wizard: Object):  # pylint: disable=redefined-outer-name
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\nprint(api.caller)"
        code.r_exec(src, {}, globals)
        assert printed == ['#2 (Wizard)']
