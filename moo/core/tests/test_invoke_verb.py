import pytest

from .. import code, parse
from ..models import Object, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_caller_can_invoke_trivial_verb(t_init: Object, t_wizard: Object):
    printed = []
    description = t_wizard.location.properties.get(name="description")

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        writer = code.context.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        src = "from moo.core import api\napi.caller.invoke_verb('inspect')"
        code.r_exec(src, {}, globals)
        assert printed == [description.value]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_is_null_when_using_parser(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        parse.interpret("test-args-parser")
    assert printed == ["PARSER"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_is_not_null_when_using_eval(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    verb = Verb.objects.get(names__name="test-args")
    with code.context(t_wizard, _writer):
        code.interpret(verb.code)
    assert printed == ["METHOD:():{}"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_when_calling_multiple_verbs(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        parse.interpret("test-nested-verbs")
    assert printed == list(range(1, 11))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_write_to_caller(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        with pytest.warns(RuntimeWarning, match=r"ConnectionError\(\#3 \(Wizard\)\)\: TEST_STRING"):
            code.interpret("from moo.core import api, write\nwrite(api.caller, 'TEST_STRING')")
