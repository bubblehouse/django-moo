import pathlib

import pytest

from moo.core import code, create, lookup, parse
from moo.core.models import Object
from moo.core.models.verb import Repository, Verb, VerbName
from moo.bootstrap import load_verb_source


# --- @edit / edit_callback ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_verb_opens_editor(t_init: Object, t_wizard: Object):
    """@edit <verb> on <obj> opens the editor (publishes editor event) when the verb exists."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("hello")')
        VerbName.objects.create(verb=v, name="myverb")
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@edit myverb on widget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_opens_editor(t_init: Object, t_wizard: Object):
    """@edit <prop> on <obj> opens the editor (publishes editor event) when the property exists."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        obj.set_property("myprop", "hello")
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@edit myprop on widget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_nonexistent_attribute_prints_error(t_init: Object, t_wizard: Object):
    """@edit <bogus> on <obj> prints an error when the attribute doesn't exist."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@edit bogus on widget")
    assert any("bogus" in str(m) for m in printed)
    assert any("widget" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_callback_updates_verb_code(t_init: Object, t_wizard: Object):
    """edit_callback saves new content to verb.code when obj.kind == 'verb'."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("original")')
        VerbName.objects.create(verb=v, name="myverb")
        programmer = system.get_property("programmer")
        callback = programmer.get_verb("edit_callback")
        callback('print("updated")', v.pk, "verb")
    v.refresh_from_db()
    assert "updated" in v.code


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_callback_updates_property_value(t_init: Object, t_wizard: Object):
    """edit_callback saves new content to property.value when obj.kind == 'property'."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        obj.set_property("myprop", "original")
        prop = obj.get_property("myprop", recurse=False, original=True)
        programmer = system.get_property("programmer")
        callback = programmer.get_verb("edit_callback")
        callback("updated", prop.pk, "property")
    prop.refresh_from_db()
    assert prop.value == "updated"


def _write_verb_file(path: pathlib.Path, on: str, verb_name: str, body: str) -> pathlib.Path:
    """Write a minimal verb source file to *path* and return it."""
    path.write_text(f"#!moo verb {verb_name} --on {on}\n{body}\n", encoding="utf8")
    return path


# --- @reload ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_updates_verb_code(t_init: Object, t_wizard: Object, tmp_path):
    """@reload updates verb code in the DB when the source file has changed."""
    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)

        verb_file = tmp_path / "myverb.py"
        _write_verb_file(verb_file, "widget", "myverb", 'print("original")')
        load_verb_source(verb_file, system, repo)

        assert obj.has_verb("myverb")
        assert "original" in obj.get_verb("myverb").code

        # Modify the file on disk then reload via the verb
        _write_verb_file(verb_file, "widget", "myverb", 'print("updated")')
        parse.interpret(ctx, "@reload myverb on widget")

    obj.refresh_from_db()
    assert "updated" in obj.get_verb("myverb").code


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_nonexistent_verb_no_output(t_init: Object, t_wizard: Object, tmp_path):
    """@reload on a verb that doesn't exist produces no output and no exception."""
    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)

        verb_file = tmp_path / "myverb.py"
        _write_verb_file(verb_file, "widget", "myverb", 'print("hello")')
        load_verb_source(verb_file, system, repo)

        parse.interpret(ctx, "@reload bogusverb on widget")
    assert printed == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_verb_without_filename_raises(t_init: Object, t_wizard: Object):
    """@reload on a verb with no filename/repo raises RuntimeError."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("hi")')
        VerbName.objects.create(verb=v, name="myverb")
        with pytest.raises(RuntimeError):
            parse.interpret(ctx, "@reload myverb on widget")
