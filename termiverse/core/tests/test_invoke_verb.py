from .. import code
from ..models import Object
from . import termiverse_init

import pytest

@pytest.mark.django_db
def test_dir(termiverse_init):
    user = Object.objects.get(name='Wizard')
    def _writer(msg):
        raise Exception("print called")
    with code.context(user, _writer):
        writer = code.get_output()
        locals = {}
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("dir()", locals, globals)
        assert result == []

@pytest.mark.django_db
def test_print(termiverse_init):
    printed = []
    user = Object.objects.get(name='Wizard')
    def _writer(msg):
        printed.append(msg)
    with code.context(user, _writer):
        writer = code.get_output()
        locals = {}
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        result = code.do_eval("print('test')", locals, globals)
        assert result is None
        assert printed == ['test']

@pytest.mark.django_db
def test_caller_print(termiverse_init):
    printed = []
    user = Object.objects.get(name='Wizard')
    def _writer(msg):
        printed.append(msg)
    with code.context(user, _writer):
        writer = code.get_output()
        locals = {}
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\nprint(api.caller)"
        code.r_exec(src, locals, globals)
        assert printed == ['#2 (Wizard)']

@pytest.mark.django_db
def test_caller_look(termiverse_init):
    printed = []
    user = Object.objects.get(name='Wizard')
    location = user.location
    description = location.properties.get(name="description")
    def _writer(msg):
        printed.append(msg)
    with code.context(user, _writer):
        writer = code.get_output()
        locals = {}
        globals = code.get_default_globals()
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\napi.caller.invoke_verb('look')"
        code.r_exec(src, locals, globals)
        assert printed == [description.value]
