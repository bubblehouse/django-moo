import logging

import pytest
from django.test import override_settings

from moo.tests import *  # pylint: disable=wildcard-import
from ..models import Object, Verb
from .. import code, parse

@pytest.mark.django_db
def test_caller_can_invoke_trivial_verb(t_init: Object, t_wizard: Object):
    printed = []
    description = t_wizard.location.properties.get(name="description")
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        src = "from moo.core import api\napi.caller.invoke_verb('look')"
        code.r_exec(src, {}, globals)
        assert printed == [description.value]

@pytest.mark.django_db
def test_args_is_null_when_using_parser(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("test-args")
    assert printed == ["PARSER"]

@pytest.mark.django_db
def test_args_is_not_null_when_using_eval(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    verb = Verb.objects.filter(names__name="test-args")
    with code.context(t_wizard, _writer):
        code.interpret(verb[0].code)
    assert printed == ["METHOD:():{}"]

@pytest.mark.django_db
def test_args_when_calling_multiple_verbs(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        parse.interpret("test-nested-verbs")
    assert printed == list(range(1, 11))

@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_STORE_EAGER_RESULT=True)
def test_simple_async_verb(t_init: Object, t_wizard: Object, caplog):
    printed = []
    def _writer(msg):
        printed.append(msg)
    verb = Verb.objects.filter(names__name="test-async-verbs")[0]
    with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
        with code.context(t_wizard, _writer):
            verb()
    counter = 1
    assert printed == [counter]
    for line in caplog.text.split("\n"):
        if not line:
            continue
        counter += 1
        assert line.endswith(str(counter))
