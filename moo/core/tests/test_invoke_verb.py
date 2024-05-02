import pytest

from moo.tests import *  # pylint: disable=wildcard-import
from ..models import Object, Verb
from .. import code, parse, api

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
        lex = parse.Lexer("test-args")
        parser = parse.Parser(lex, t_wizard)
        verb = parser.get_verb()
        globals = code.get_restricted_environment(code.context.get('writer'))  # pylint: disable=redefined-builtin
        #TODO: this should be done centrally by making this a reusable function
        api.parser = parser
        code.r_exec(verb.code, {}, globals, filename=repr(verb))
        assert printed == ["PARSER"]

@pytest.mark.django_db
def test_args_is_not_null_when_using_eval(t_init: Object, t_wizard: Object):
    printed = []
    def _writer(msg):
        printed.append(msg)
    with code.context(t_wizard, _writer):
        writer = code.context.get('writer')
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment(writer))
        verb = Verb.objects.filter(names__name="test-args")
        #TODO: this should be done centrally by making this a reusable function
        api.args = ()
        api.kwargs = {}
        code.r_exec(verb[0].code, {}, globals)
        assert printed == ["METHOD"]
