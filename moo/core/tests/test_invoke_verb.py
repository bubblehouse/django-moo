import pytest

from .. import code, parse, create
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
        globals.update(code.get_restricted_environment("__main__", writer))
        src = "from moo.core import api\napi.caller.invoke_verb('inspect')"
        code.r_exec(src, {}, globals)
        assert printed == [description.value]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_override_verb_in_subclass(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        root = create("Root Class")
        root.add_verb("accept", code="return False")
        room = create("Test Room", parents=[root], location=None)
        with pytest.raises(PermissionError):
            test_obj = create("Test Object", location=room)
        room.add_verb("accept", code="return True")
        test_obj = create("Test Object", location=room)
        assert test_obj.location == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_is_null_when_using_parser(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "test-args-parser")
    assert printed == ["PARSER"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_is_not_null_when_using_eval(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    verb = Verb.objects.get(names__name="test-args")
    with code.context(t_wizard, _writer):
        code.interpret(verb.code, "__main__")
    assert printed == ["METHOD:():{}"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_args_when_calling_multiple_verbs(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer) as ctx:
        parse.interpret(ctx, "test-nested-verbs")
    assert printed == list(range(1, 11))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_write_to_caller(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        with pytest.warns(RuntimeWarning, match=r"ConnectionError\(\#3 \(Wizard\)\)\: TEST_STRING"):
            code.interpret("from moo.core import api, write\nwrite(api.caller, 'TEST_STRING')", "__main__")

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_with_wildard(t_init: Object, t_wizard: Object):
    box = Object.objects.create(name="box")
    box.location = t_wizard.location
    box.save()
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        lex = parse.Lexer("desc box")
        parser = parse.Parser(lex, t_wizard)
        verb = parser.get_verb()
        assert verb.names.filter(name="describe").exists()

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_passthrough(t_init: Object, t_wizard: Object):
    superbox = create(name="superbox", owner=t_wizard)
    superbox.location = t_wizard.location
    superbox.save()

    box = create(name="box", parents=[superbox], owner=t_wizard)
    box.location = t_wizard.location
    box.save()

    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        superbox.add_verb("testpassthrough", code="""return "Superbox verb." """)
        box.add_verb("testpassthrough", code="""return "%s with some extra stuff." % passthrough() """)
        result = box.invoke_verb("testpassthrough")
        assert result == "Superbox verb. with some extra stuff."
