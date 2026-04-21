# pylint: disable=protected-access
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
def test_edit_verb_with_malformed_shebang_prints_error(t_init: Object, t_wizard: Object):
    """@edit verb on <obj> with a malformed #!moo shebang prints an error and does not create the verb."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(ctx, "@edit verb newverb on widget with \"#!moo verb newverb --dsppec any\\nprint('hi')\"")
    assert any("malformed shebang" in str(m).lower() or "Error:" in str(m) for m in printed)
    obj.refresh_from_db()
    assert not obj.has_verb("newverb", recurse=False)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_verb_with_valid_shebang_sets_dspec(t_init: Object, t_wizard: Object):
    """@edit verb on <obj> with a valid shebang sets direct_object on the created verb."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        parse.interpret(
            ctx, "@edit verb newverb on widget with \"#!moo verb newverb --on $thing --dspec any\\nprint('hi')\""
        )
    obj.refresh_from_db()
    assert obj.has_verb("newverb", recurse=False)
    v = obj.get_verb("newverb", recurse=False)
    assert v.direct_object == "any"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_callback_malformed_shebang_prints_error(t_init: Object, t_wizard: Object):
    """edit_callback with a malformed #!moo shebang prints an error and does not save the verb."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("original")', direct_object="none")
        VerbName.objects.create(verb=v, name="myverb")
        programmer = system.get_property("programmer")
        callback = programmer.get_verb("edit_callback")
        callback("#!moo verb myverb --dsppec any\nprint('hi')", v.pk, "verb")
    v.refresh_from_db()
    assert any("malformed shebang" in str(m).lower() or "Error:" in str(m) for m in printed)
    assert "original" in v.code


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_callback_valid_shebang_sets_dspec(t_init: Object, t_wizard: Object):
    """edit_callback with a valid shebang updates direct_object on the verb."""
    system = lookup(1)
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("original")', direct_object="none")
        VerbName.objects.create(verb=v, name="myverb")
        programmer = system.get_property("programmer")
        callback = programmer.get_verb("edit_callback")
        callback("#!moo verb myverb --on $thing --dspec any\nprint('updated')", v.pk, "verb")
    v.refresh_from_db()
    assert "updated" in v.code
    assert v.direct_object == "any"


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
def test_edit_verb_with_creates_verb_on_thing_child(t_init: Object, t_wizard: Object):
    """@edit verb <inherited-name> on <$thing child> with <content> creates verb directly on child."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("clock", parents=[system.thing], location=t_wizard.location)
        # moveto is inherited from $root_class via $thing; should create directly on clock
        parse.interpret(ctx, '@edit verb moveto on clock with "return False"')
    obj.refresh_from_db()
    assert obj.has_verb("moveto", recurse=False)
    v = obj.get_verb("moveto", recurse=False)
    assert "return False" in v.code
    assert any("Created verb moveto" in str(m) for m in printed)


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_edit_property_where_name_matches_inherited_verb(t_init: Object, t_wizard: Object):
    """@edit property <name> on <obj> with <content> creates a new property even when
    an inherited verb with the same name exists on the parent."""
    lookup(1)
    furniture = lookup("$furniture")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        obj = create("test settee", parents=[furniture], location=t_wizard.location)
        # sit_succeeded_msg is a verb on $furniture, not a property — this should
        # still create the property cleanly and print a confirmation.
        parse.interpret(ctx, '@edit property sit_succeeded_msg on "test settee" with "You sink in. It holds."')
    obj.refresh_from_db()
    assert obj.has_property("sit_succeeded_msg")
    prop = obj.get_property("sit_succeeded_msg", recurse=False, original=True)
    assert prop.value == '"You sink in. It holds."'
    assert any("sit_succeeded_msg" in str(m) for m in printed), f"No confirmation in output: {printed}"


def _write_verb_file(path: pathlib.Path, on: str, verb_name: str, body: str) -> pathlib.Path:
    """Write a minimal verb source file to *path* and return it."""
    path.write_text(f"#!moo verb {verb_name} --on {on}\n{body}\n", encoding="utf8")
    return path


# ---------------------------------------------------------------------------
# Raw-mode @edit hint (MUD-client mode)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_edit_verb_raw_mode_hints_with_form(t_init: Object, t_wizard: Object):
    """In raw mode, @edit <verb> on <obj> (no `with`) prints the inline-form hint and does not publish an editor event."""
    from moo.shell import prompt as prompt_module

    system = lookup(1)
    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            obj = create("widget", parents=[system.root_class], location=t_wizard.location)
            v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("hello")')
            VerbName.objects.create(verb=v, name="myverb")
            parse.interpret(ctx, "@edit myverb on widget")
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    assert any("Raw mode" in str(m) and "with" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_edit_property_raw_mode_hints_with_form(t_init: Object, t_wizard: Object):
    """In raw mode, @edit property <name> on <obj> (no `with`) prints the property-form hint."""
    from moo.shell import prompt as prompt_module

    system = lookup(1)
    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            obj = create("widget", parents=[system.root_class], location=t_wizard.location)
            obj.set_property("myprop", "hello")
            parse.interpret(ctx, "@edit property myprop on widget")
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    assert any("Raw mode" in str(m) and "property" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_edit_verb_raw_mode_with_form_still_works(t_init: Object, t_wizard: Object):
    """The inline `with` form succeeds in raw mode — the hint is gated on absence of `with`."""
    from moo.shell import prompt as prompt_module

    system = lookup(1)
    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            obj = create("widget", parents=[system.root_class], location=t_wizard.location)
            v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("original")')
            VerbName.objects.create(verb=v, name="myverb")
            parse.interpret(ctx, '@edit myverb on widget with print("updated")')
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    v.refresh_from_db()
    assert "updated" in v.code
    assert not any("Raw mode" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_edit_rich_mode_still_opens_editor(t_init: Object, t_wizard: Object):
    """In rich mode (default), @edit without `with` still publishes an editor event."""
    from moo.shell import prompt as prompt_module

    system = lookup(1)
    prompt_module._session_settings.pop(t_wizard.owner.pk, None)  # explicit rich (default)
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        obj = create("widget", parents=[system.root_class], location=t_wizard.location)
        v = Verb.objects.create(origin=obj, owner=t_wizard, code='print("hello")')
        VerbName.objects.create(verb=v, name="myverb")
        with pytest.warns(RuntimeWarning):
            parse.interpret(ctx, "@edit myverb on widget")
