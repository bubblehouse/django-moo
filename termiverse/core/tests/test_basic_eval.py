from termiverse.core.models.object import Object
from termiverse.tests import *
from .. import code

import pytest

@pytest.mark.django_db
def test_dir(t_init: Object, t_wizard: Object):
    def _writer(msg):
        raise Exception("print was called unexpectedly")
    with code.context(t_wizard, _writer):
        writer = code.get_output()
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("dir()", {}, globals)
        assert result == []

@pytest.mark.django_db
def test_print(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.get_output()
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("print('test')", {}, globals)
        assert result is None
        assert printed == ['test']

@pytest.mark.django_db
def test_caller_print(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.get_output()
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\nprint(api.caller)"
        code.r_exec(src, {}, globals)
        assert printed == ['#2 (Wizard)']
