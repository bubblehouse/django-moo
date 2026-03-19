import pathlib

import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object, Player
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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_verb_prefix_explicitly_edits_verb(t_init: Object, t_wizard: Object):
    """@edit verb <name> on <obj> opens editor for the verb even if property exists."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("verb")')
        VerbName.objects.create(verb=v, name="name")
        obj.set_property("name", "property")
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@edit verb name on widget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_prefix_explicitly_edits_property(t_init: Object, t_wizard: Object):
    """@edit property <name> on <obj> opens editor for the property even if verb exists."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("verb")')
        VerbName.objects.create(verb=v, name="name")
        obj.set_property("name", "property")
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@edit property name on widget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_with_sets_existing_verb_directly(t_init: Object, t_wizard: Object):
    """@edit <verb> on <obj> with <content> updates verb without opening editor."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("original")')
        VerbName.objects.create(verb=v, name="myverb")
        parse.interpret(ctx, '@edit myverb on widget with print("updated")')
    v.refresh_from_db()
    assert "updated" in v.code
    assert any("Set verb myverb" in str(m) and "widget" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_with_sets_existing_property_directly(t_init: Object, t_wizard: Object):
    """@edit <prop> on <obj> with <content> updates property without opening editor."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        obj.set_property("myprop", "original")
        # User types: with "updated" → parser gives: updated → we JSON-encode to: "updated"
        parse.interpret(ctx, '@edit myprop on widget with "updated"')
    prop = obj.get_property("myprop", recurse=False, original=True)
    assert prop.value == '"updated"'
    assert any("Set property myprop" in str(m) and "widget" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_verb_with_creates_new_verb(t_init: Object, t_wizard: Object):
    """@edit verb <name> on <obj> with <content> creates new verb."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, '@edit verb newverb on widget with print("new")')
    obj.refresh_from_db()
    assert obj.has_verb("newverb")
    v = obj.get_verb("newverb")
    assert "new" in v.code
    assert any("Created verb newverb" in str(m) and "widget" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_with_creates_new_property(t_init: Object, t_wizard: Object):
    """@edit property <name> on <obj> with <content> creates new property."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        # User types: with "newvalue" → parser gives: newvalue → we JSON-encode to: "newvalue"
        parse.interpret(ctx, '@edit property newprop on widget with "newvalue"')
    obj.refresh_from_db()
    assert obj.has_property("newprop")
    prop = obj.get_property("newprop", recurse=False, original=True)
    assert prop.value == '"newvalue"'
    assert any("Created property newprop" in str(m) and "widget" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_with_nonexistent_requires_type_prefix(t_init: Object, t_wizard: Object):
    """@edit <nonexistent> on <obj> with <content> prints error requiring type prefix."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@edit bogus on widget with content")
    assert any("bogus" in str(m) and "prefix" in str(m).lower() for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_verb_nonexistent_without_with_prints_error(t_init: Object, t_wizard: Object):
    """@edit verb <nonexistent> on <obj> (without 'with') prints error for missing verb."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@edit verb bogus on widget")
    assert any("bogus" in str(m) and "not a verb" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_nonexistent_without_with_prints_error(t_init: Object, t_wizard: Object):
    """@edit property <nonexistent> on <obj> (without 'with') prints error for missing property."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@edit property bogus on widget")
    assert any("bogus" in str(m) and "not a property" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_with_json_array(t_init: Object, t_wizard: Object):
    """@edit property with JSON array stores it correctly."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        # User types array literal → parser gives us the string → we store as-is
        parse.interpret(ctx, '@edit property lines on widget with ["Yeah?", "What\'ll it be?"]')
    obj.refresh_from_db()
    prop = obj.get_property("lines", recurse=False, original=True)
    assert prop.value == '["Yeah?", "What\'ll it be?"]'
    assert any("Created property lines" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_with_json_boolean(t_init: Object, t_wizard: Object):
    """@edit property with JSON boolean stores it correctly."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        # User types: with true → parser gives: true → we store as-is (valid JSON)
        parse.interpret(ctx, "@edit property full on widget with true")
    obj.refresh_from_db()
    prop = obj.get_property("full", recurse=False, original=True)
    assert prop.value == "true"
    assert any("Created property full" in str(m) for m in printed)


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
    assert not printed


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_object_reloads_all_verbs(t_init: Object, t_wizard: Object, tmp_path):
    """@reload <object> updates all filesystem verbs on that object."""
    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widget", parents=[system.root_class], location=t_wizard.location)

        verb_file1 = tmp_path / "verb1.py"
        _write_verb_file(verb_file1, "widget", "verb1", 'print("original1")')
        load_verb_source(verb_file1, system, repo)

        verb_file2 = tmp_path / "verb2.py"
        _write_verb_file(verb_file2, "widget", "verb2", 'print("original2")')
        load_verb_source(verb_file2, system, repo)

        _write_verb_file(verb_file1, "widget", "verb1", 'print("updated1")')
        _write_verb_file(verb_file2, "widget", "verb2", 'print("updated2")')
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@reload widget")

    obj = lookup("widget")
    assert "updated1" in obj.get_verb("verb1").code
    assert "updated2" in obj.get_verb("verb2").code
    assert any("2 verb(s) on widget" in str(warning.message) for warning in w)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_all_reloads_all_verbs(t_init: Object, t_wizard: Object, tmp_path):
    """@reload all updates all filesystem verbs across all objects."""
    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("widgetA", parents=[system.root_class], location=t_wizard.location)
        create("widgetB", parents=[system.root_class], location=t_wizard.location)

        verb_file1 = tmp_path / "verbA.py"
        _write_verb_file(verb_file1, "widgetA", "verbA", 'print("originalA")')
        load_verb_source(verb_file1, system, repo)

        verb_file2 = tmp_path / "verbB.py"
        _write_verb_file(verb_file2, "widgetB", "verbB", 'print("originalB")')
        load_verb_source(verb_file2, system, repo)

        _write_verb_file(verb_file1, "widgetA", "verbA", 'print("updatedA")')
        _write_verb_file(verb_file2, "widgetB", "verbB", 'print("updatedB")')
        with pytest.warns(RuntimeWarning) as w:
            parse.interpret(ctx, "@reload all")

    assert "updatedA" in lookup("widgetA").get_verb("verbA").code
    assert "updatedB" in lookup("widgetB").get_verb("verbB").code
    assert any("Reloaded" in str(warning.message) for warning in w)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_object_not_found_prints_error(t_init: Object, t_wizard: Object):
    """@reload <unknown-object> prints an error message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@reload nonexistent_thing_xyz")
    assert any("nonexistent_thing_xyz" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_object_permission_denied(t_init: Object, t_wizard: Object, tmp_path):
    """@reload <object> is denied for a non-wizard player who doesn't own the object."""
    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    with code.ContextManager(t_wizard, lambda _: None):
        create("widget", parents=[system.root_class], location=t_wizard.location)
        verb_file = tmp_path / "myverb.py"
        _write_verb_file(verb_file, "widget", "myverb", 'print("original")')
        load_verb_source(verb_file, system, repo)
        non_wiz = create("NonWizProg", parents=[system.programmer], location=t_wizard.location)
        Player.objects.create(avatar=non_wiz, wizard=False)

    printed = []
    with code.ContextManager(non_wiz, printed.append) as ctx:
        parse.interpret(ctx, "@reload widget")
    assert any("Permission denied" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_all_schedules_continuation_on_low_time(t_init: Object, t_wizard: Object, tmp_path):
    """@reload all calls invoke() with remaining verb PKs when task_time.remaining hits threshold."""
    import moo.sdk as sdk
    from unittest.mock import patch, PropertyMock
    from moo.core.code import TaskTime

    system = lookup(1)
    repo = Repository.objects.create(slug="test-repo", prefix="test", url="http://example.com")

    # Create three filesystem verbs across three objects. The default bootstrap also
    # loads filesystem verbs, so all_pks below will include those too — that's intentional,
    # since @reload all operates on every filesystem verb in the DB.
    with code.ContextManager(t_wizard, lambda _: None):
        for letter in "ABC":
            create(f"widget{letter}", parents=[system.root_class], location=t_wizard.location)
            verb_file = tmp_path / f"verb{letter}.py"
            _write_verb_file(verb_file, f"widget{letter}", f"verb{letter}", f'print("{letter}")')
            load_verb_source(verb_file, system, repo)

    # Snapshot the full set of filesystem verb PKs now, before the reload. The verb
    # processes them in this same set, so we can verify the handoff list is exactly
    # "everything except the one that was processed before time ran out."
    all_pks = set(
        Verb.objects.filter(filename__isnull=False, repo__isnull=False)
        .exclude(filename="")
        .values_list("pk", flat=True)
    )

    # Simulate task_time returning different remaining-time values on successive reads.
    # The verb checks context.task_time before processing each verb in the loop:
    #   - first check: 0.9s remaining → above TIME_THRESHOLD (0.5s), so process the verb
    #   - second check: 0.1s remaining → at/below threshold, so hand off the rest
    task_time_values = iter(
        [
            TaskTime(elapsed=0.1, time_limit=1.0, remaining=0.9),  # first verb: enough time
            TaskTime(elapsed=0.9, time_limit=1.0, remaining=0.1),  # second verb: hand off
        ]
    )

    # patch.object on type(sdk.context) replaces the data descriptor on the _Context class,
    # so every access to context.task_time inside the verb calls mock_tt() instead.
    # patch("moo.sdk.invoke") intercepts the continuation call the verb makes; because
    # verbs re-execute their imports on every call, the patched function is what the verb
    # binds when it runs `from moo.sdk import invoke`.
    # pytest.warns captures the RuntimeWarning that context.player.tell() emits in the
    # test environment (write() can't reach a real connection, so it warns instead).
    with patch.object(type(sdk.context), "task_time", new_callable=PropertyMock) as mock_tt:
        mock_tt.side_effect = lambda: next(task_time_values, TaskTime(0.9, 1.0, 0.1))
        with patch("moo.sdk.invoke") as mock_invoke:
            with pytest.warns(RuntimeWarning):
                with code.ContextManager(t_wizard, lambda _: None) as ctx:
                    parse.interpret(ctx, "@reload all")

    # invoke() should have been called exactly once with the list of un-processed PKs
    # and the @reload verb object as the keyword argument.
    assert mock_invoke.call_count == 1
    invoke_args, invoke_kwargs = mock_invoke.call_args
    remaining_pks = invoke_args[0]
    assert isinstance(remaining_pks, list)
    assert len(remaining_pks) == len(all_pks) - 1  # all but the one verb that completed
    assert set(remaining_pks).issubset(all_pks)
    assert "verb" in invoke_kwargs


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_reload_all_permission_denied(t_init: Object, t_wizard: Object):
    """@reload all is denied for a non-wizard player."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        non_wiz = create("NonWizProg", parents=[system.programmer], location=t_wizard.location)
        Player.objects.create(avatar=non_wiz, wizard=False)

    printed = []
    with code.ContextManager(non_wiz, printed.append) as ctx:
        parse.interpret(ctx, "@reload all")
    assert any("Permission denied" in str(m) for m in printed)


# --- @eval ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_verb_exists(t_init: Object, t_wizard: Object):
    """@eval verb exists on $programmer."""
    system = lookup(1)
    programmer = system.get_property("programmer")
    # This should not raise NoSuchVerbError
    eval_verb = programmer.get_verb("@eval")
    assert eval_verb is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_simple_expression(t_init: Object, t_wizard: Object):
    """@eval evaluates simple expressions and prints the result."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "1 + 1"')
    assert any("2" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_with_import(t_init: Object, t_wizard: Object):
    """@eval can import from allowed modules."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "from moo.sdk import lookup; lookup(1)"')
    # Should print the system object repr
    assert any("Object" in str(m) or "#1" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_has_context_access(t_init: Object, t_wizard: Object):
    """@eval has access to context variables."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "from moo.sdk import context; context.player.name"')
    assert any("Wizard" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_syntax_error(t_init: Object, t_wizard: Object):
    """@eval handles syntax errors gracefully."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "1 +"')
    assert any("SyntaxError" in str(m) or "Error" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_runtime_error(t_init: Object, t_wizard: Object):
    """@eval handles runtime errors gracefully."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "1 / 0"')
    assert any("ZeroDivisionError" in str(m) or "Error" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_multiline_with_semicolons(t_init: Object, t_wizard: Object):
    """@eval can handle multiple statements with semicolons."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "x = 5; y = 3; x + y"')
    assert any("8" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_with_print(t_init: Object, t_wizard: Object):
    """@eval code can use print() which goes to the player."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@eval \"print('hello world')\"")
    assert any("hello world" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_respects_sandbox(t_init: Object, t_wizard: Object):
    """@eval respects sandbox restrictions (no os module)."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "import os"')
    assert any("ImportError" in str(m) or "Error" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_returns_none_no_output(t_init: Object, t_wizard: Object):
    """@eval does not print None results."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@eval "None"')
    # Should not print "None" - only non-None results are printed
    assert not any(str(m).strip() == "None" for m in printed)
