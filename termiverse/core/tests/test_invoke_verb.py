from termiverse.tests import *
from ..models import Object
from .. import code

import pytest

@pytest.mark.django_db
def test_caller_look(t_init: Object, t_wizard: Object):
    printed = []
    description = t_wizard.location.properties.get(name="description")
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.get_output()
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\napi.caller.invoke_verb('look')"
        code.r_exec(src, {}, globals)
        assert printed == [description.value]
