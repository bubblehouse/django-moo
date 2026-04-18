import pytest

from moo.core import code, parse
from moo.core.exceptions import NoSuchPropertyError
from moo.sdk import create, lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_verb_exists(t_init: Object, t_wizard: Object):
    system = lookup(1)
    builder = system.get_property("builder")
    assert builder.get_verb("@set") is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_creates_int_property(t_init: Object, t_wizard: Object):
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@set count on widget to 42")
    widget.refresh_from_db()
    assert widget.get_property("count") == 42
    assert any("42" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_updates_existing_property(t_init: Object, t_wizard: Object):
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@set count on widget to 42")
        parse.interpret(ctx, "@set count on widget to 99")
    widget.refresh_from_db()
    assert widget.get_property("count") == 99


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_stores_string(t_init: Object, t_wizard: Object):
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, '@set label on widget to "Hello"')
    widget.refresh_from_db()
    assert widget.get_property("label") == "Hello"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_stores_object_reference(t_init: Object, t_wizard: Object):
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, '@set target on widget to lookup("$wizard")')
    widget.refresh_from_db()
    target = widget.get_property("target")
    assert isinstance(target, Object)
    assert target.pk == system.get_property("wizard").pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_stores_list(t_init: Object, t_wizard: Object):
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@set items on widget to [1, 2, 3]")
    widget.refresh_from_db()
    assert widget.get_property("items") == [1, 2, 3]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_resolves_hash_reference(t_init: Object, t_wizard: Object):
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, f"@set count on #{widget.pk} to 7")
    widget.refresh_from_db()
    assert widget.get_property("count") == 7


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_resolves_dollar_reference(t_init: Object, t_wizard: Object):
    system = lookup(1)
    wizard = system.get_property("wizard")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "@set scratch on $wizard to 1")
    wizard.refresh_from_db()
    assert wizard.get_property("scratch") == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_missing_to_prints_usage(t_init: Object, t_wizard: Object):
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@set count on widget")
    assert any("Usage:" in str(m) for m in printed)
    widget.refresh_from_db()
    with pytest.raises(NoSuchPropertyError):
        widget.get_property("count", recurse=False)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_unknown_object(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@set count on nosuch to 1")
    assert any("nosuch" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_value_expression_error(t_init: Object, t_wizard: Object):
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        widget = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@set count on widget to 1 +")
    assert any("Error evaluating value" in str(m) for m in printed)
    widget.refresh_from_db()
    with pytest.raises(NoSuchPropertyError):
        widget.get_property("count", recurse=False)
