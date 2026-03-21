import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.core.models.property import Property
from moo.sdk import create, lookup


def setup_obj(t_wizard: Object, name: str = "test box") -> Object:
    system = lookup(1)
    return create(name, parents=[system.thing], location=t_wizard.location)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_as_sets_description(t_init: Object, t_wizard: Object):
    """@describe OBJ as TEXT stores the description on the object."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        parse.interpret(ctx, '@describe test box as "A plain wooden box."')
        obj.refresh_from_db()
        assert obj.get_property("description") == "A plain wooden box."
        assert any("Description set" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_as_newline_escape(t_init: Object, t_wizard: Object):
    """@describe OBJ as TEXT converts \\n escape sequences to real newlines."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        parse.interpret(ctx, r'@describe test box as "Line one.\nLine two."')
        obj.refresh_from_db()
        assert obj.get_property("description") == "Line one.\nLine two."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_no_dobj_does_not_match(t_init: Object, t_wizard: Object):
    """@describe with no object does not match the verb (--dspec any requires a dobj)."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@describe")
        # Verb requires a dobj; without one the parser emits a dspec error
        assert any("requires a direct object" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_no_as_opens_editor_with_existing_description(t_init: Object, t_wizard: Object):
    """@describe OBJ without 'as' opens the editor pre-populated with the current description."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        obj.describe("Old description.")
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@describe test box")
        messages = [str(warning.message) for warning in w.list]
        assert any("editor" in m for m in messages)
        assert any("Old description." in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_no_as_opens_editor_with_empty_content_when_no_description(t_init: Object, t_wizard: Object):
    """@describe OBJ without 'as' opens the editor with empty content when no description is set."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = setup_obj(t_wizard)
        Property.objects.filter(origin=obj, name="description").delete()
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@describe test box")
        messages = [str(warning.message) for warning in w.list]
        assert any("editor" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_callback_sets_description(t_init: Object, t_wizard: Object):
    """describe_callback stores the editor's saved text as the object's description."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = setup_obj(t_wizard)
        t_wizard.describe_callback("A freshly written description.", obj.pk)
        obj.refresh_from_db()
        assert obj.get_property("description") == "A freshly written description."
        assert any("Description set" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_describe_callback_overwrites_existing_description(t_init: Object, t_wizard: Object):
    """describe_callback replaces an existing description."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = setup_obj(t_wizard)
        obj.describe("Old description.")
        t_wizard.describe_callback("New description.", obj.pk)
        obj.refresh_from_db()
        assert obj.get_property("description") == "New description."
