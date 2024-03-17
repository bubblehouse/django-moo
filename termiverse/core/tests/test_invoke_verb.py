import pytest

from termiverse.tests import *  # pylint: disable=wildcard-import
from ..models import Object
from .. import code

@pytest.mark.django_db
def test_caller_can_invoke_trivial_verb(t_init: Object, t_wizard: Object):  # pylint: disable=redefined-outer-name
    printed = []
    description = t_wizard.location.properties.get(name="description")
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\napi.caller.invoke_verb('look')"
        code.r_exec(src, {}, globals)
        assert printed == [description.value]
