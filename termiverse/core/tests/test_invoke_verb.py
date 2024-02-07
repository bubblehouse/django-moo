import importlib.resources

from termiverse.core import code
from termiverse.core.models import Repository, Object, Player
from termiverse.core.bootstrap import load_python

import pytest
from django.contrib.auth.models import User
from django.conf import settings

@pytest.fixture()
def termiverse_init():
    Repository.objects.create(
        slug='default',
        prefix='termiverse/core/bootstrap/default_verbs',
        url=settings.DEFAULT_GIT_REPO_URL
    )
    ref = importlib.resources.files('termiverse.core.bootstrap') / 'default.py'
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    user = User.objects.create(username='phil')
    avatar = Object.objects.get(name='Wizard')
    Player.objects.create(user=user, avatar=avatar)
    yield "termiverse_init"

@pytest.mark.django_db
def test_dir(termiverse_init):
    user = Object.objects.get(name='Wizard')
    def _writer(msg):
        raise Exception("print called")
    with code.context(user, _writer):
        writer = code.get_output()
        caller = code.get_caller()
        locals = {}
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None
        }
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
        caller = code.get_caller()
        locals = {}
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None
        }
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
        caller = code.get_caller()
        locals = {}
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None
        }
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
        caller = code.get_caller()
        locals = {}
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None
        }
        globals.update(code.get_restricted_environment(writer))
        src = "from termiverse.core import api\napi.caller.invoke_verb('look')"
        code.r_exec(src, locals, globals)
        assert printed == [description.value]
