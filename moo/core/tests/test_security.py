# -*- coding: utf-8 -*-
"""
Security tests for the verb execution sandbox.

Each test documents a specific attack surface. Passing tests confirm that a
hole has been sealed. Any test added here as a failing test indicates a hole
that requires further work to close.
"""

import types

import pytest

from moo.core.models.object import Object

from .. import code


# ---------------------------------------------------------------------------
# Helpers (mirrors test_code.py conventions)
# ---------------------------------------------------------------------------

def _mock(is_wizard=False):
    return types.SimpleNamespace(is_wizard=lambda: is_wizard)


def _ctx(caller, writer=None):
    return code.ContextManager(caller, writer or (lambda s: None))


def _exec(src, caller=None, writer=None):
    """Run verb source in the restricted environment, return printed output."""
    caller = caller or _mock()
    printed = []
    with _ctx(caller, printed.append):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        code.r_exec(src, {}, g)
    return printed


def _raises(src, exc, caller=None):
    """Assert that running src raises the given exception."""
    caller = caller or _mock()
    with _ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(exc):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# __metaclass__ must not expose type
# ---------------------------------------------------------------------------

def test_metaclass_not_in_globals():
    """__metaclass__ was a Python 2 artifact; it must not appear in the sandbox globals."""
    caller = _mock()
    with _ctx(caller):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        assert "__metaclass__" not in g


# ---------------------------------------------------------------------------
# dir() must not be available
# ---------------------------------------------------------------------------

def test_dir_builtin_removed():
    """dir() is not in ALLOWED_BUILTINS and must raise NameError in verb code."""
    _raises("dir()", NameError)


# ---------------------------------------------------------------------------
# getattr() / hasattr() must not allow underscore names
# ---------------------------------------------------------------------------

def test_getattr_underscore_blocked():
    """getattr(obj, '__class__') must raise AttributeError, not return the class."""
    _raises("getattr('hello', '__class__')", AttributeError)


def test_getattr_normal_names_still_work():
    """getattr on a normal (non-underscore) name must still work."""
    printed = _exec("print(getattr('hello', 'upper')())")
    assert printed == ["HELLO"]


def test_hasattr_underscore_returns_false():
    """hasattr(obj, '__class__') must return False, not True."""
    printed = _exec("print(hasattr('hello', '__class__'))")
    assert printed == [False]


def test_hasattr_normal_names_still_work():
    """hasattr on a normal name must still work."""
    printed = _exec("print(hasattr('hello', 'upper'))")
    assert printed == [True]


# ---------------------------------------------------------------------------
# ORM access via getattr chain must be blocked
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dunder attribute syntax must remain blocked (regression guard)
# ---------------------------------------------------------------------------

def test_dunder_syntax_blocked():
    """
    Dunder attribute syntax (obj.__class__) is rejected at compile time by
    RestrictedPython — code.code is None, so exec raises TypeError.
    Either way, access is denied.
    """
    _raises("x = ''.__class__", (AttributeError, TypeError))


# ---------------------------------------------------------------------------
# ContextManager must not be importable via moo.core
# ---------------------------------------------------------------------------

def test_context_manager_not_importable():
    """
    ContextManager is in BLOCKED_IMPORTS for moo.sdk.
    Verb code must not be able to call override_caller() to impersonate another player.
    """
    _raises("from moo.sdk import ContextManager", ImportError)


# ---------------------------------------------------------------------------
# set_task_perms must require wizard (regression guard)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_set_task_perms_requires_wizard(t_init: Object, t_wizard: Object):
    """
    set_task_perms() raises UserError when called by a non-wizard.
    This is already enforced; test guards against regression.
    """
    from moo.sdk import set_task_perms
    from moo.core.exceptions import UserError

    # Create a plain (non-wizard) object to act as caller
    from moo.sdk import create
    plain = create("plain_user")

    with _ctx(plain):
        with pytest.raises(UserError):
            with set_task_perms(t_wizard):
                pass


# ---------------------------------------------------------------------------
# _publish_to_player must not be importable via moo.core
# ---------------------------------------------------------------------------

def test_publish_to_player_not_importable():
    """
    _publish_to_player must not be accessible from verb code.
    RestrictedPython rejects _-prefixed names at compile time (TypeError on exec),
    and BLOCKED_IMPORTS provides defense-in-depth at the import level.
    """
    _raises("from moo.sdk import _publish_to_player", (ImportError, TypeError))


# ---------------------------------------------------------------------------
# context.caller_stack must return a copy, not the live list
# ---------------------------------------------------------------------------

def test_caller_stack_returns_copy():
    """
    ContextManager.get('caller_stack') must return a copy of the stack list.
    Mutating the returned list must not affect the live _active_caller_stack.
    """
    caller = _mock()
    with _ctx(caller):
        stack_copy = code.ContextManager.get("caller_stack")
        stack_copy.append({"previous_caller": "FAKE"})
        live = code.ContextManager.get("caller_stack")
        assert "FAKE" not in [f.get("previous_caller") for f in live]


# ---------------------------------------------------------------------------
# invoke() must require wizard for persistent (periodic/cron) tasks
# ---------------------------------------------------------------------------

def test_invoke_periodic_requires_wizard():
    """invoke(..., periodic=True) raises UserError when called by a non-wizard."""
    from unittest.mock import MagicMock
    from moo.sdk import invoke
    from moo.core.exceptions import UserError

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    verb = MagicMock()

    with _ctx(non_wizard):
        with pytest.raises(UserError):
            invoke(verb=verb, delay=60, periodic=True)


def test_invoke_cron_requires_wizard():
    """invoke(..., cron=...) raises UserError when called by a non-wizard."""
    from unittest.mock import MagicMock
    from moo.sdk import invoke
    from moo.core.exceptions import UserError

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    verb = MagicMock()

    with _ctx(non_wizard):
        with pytest.raises(UserError):
            invoke(verb=verb, cron="* * * * *")


def test_invoke_oneshot_allowed_for_nonwizard():
    """invoke() without periodic/cron must not raise for non-wizards."""
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    non_wizard.pk = 42
    verb = MagicMock()
    verb.invoked_object.pk = 1
    verb.invoked_name = "test"

    with _ctx(non_wizard):
        with patch("moo.core.tasks.invoke_verb.apply_async"):
            invoke(verb=verb)


# ---------------------------------------------------------------------------
# context attributes must be read-only (descriptor shadowing guard)
# ---------------------------------------------------------------------------

def test_context_caller_is_read_only_directly():
    """
    Directly assigning context.caller must raise AttributeError.
    The _Context.descriptor is a data descriptor; instance attributes cannot shadow it.
    """
    from moo.sdk import context

    with pytest.raises(AttributeError):
        context.caller = _mock(is_wizard=True)


def test_context_caller_shadowing_blocked_in_verb():
    """
    Verb code must not be able to shadow context.caller via _write_ assignment.
    Previously, setattr(context, 'caller', wizard_obj) silently shadowed the
    non-data descriptor, making context.caller.is_wizard() return True for all
    subsequent code in the same worker process.
    """
    # Does not need DB — just tests that setattr on the context singleton is rejected.
    _raises("from moo.sdk import context\ncontext.caller = None", AttributeError)


# ---------------------------------------------------------------------------
# string module must not be importable
# ---------------------------------------------------------------------------

def test_string_module_not_importable():
    """
    'string' was removed from ALLOWED_MODULES because string.Formatter.get_field
    calls CPython's real getattr internally, bypassing safe_getattr and allowing
    dunder attribute access (e.g. __class__) to reach the Django ORM.
    """
    _raises("import string", ImportError)


# ---------------------------------------------------------------------------
# invoke() must check execute permission on the verb
# ---------------------------------------------------------------------------

def test_invoke_checks_execute_permission():
    """
    invoke() must call can_caller("execute", verb) before dispatching.
    Previously the check was missing; a caller with only read access could
    enqueue any verb they could look up.  The test uses mocks so that the
    denial is deterministic regardless of default ACL state.
    """
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    caller = MagicMock()
    caller.is_wizard.return_value = False
    caller.pk = 42

    verb = MagicMock()
    verb.invoked_name = "test"
    verb.invoked_object.can_caller.side_effect = PermissionError("no execute")

    with _ctx(caller):
        with pytest.raises(PermissionError):
            with patch("moo.core.tasks.invoke_verb.apply_async"):
                invoke(verb=verb)


# ---------------------------------------------------------------------------
# _write_.__setitem__ must block underscore keys
# ---------------------------------------------------------------------------

def test_write_setitem_underscore_key_blocked():
    """
    obj['__class__'] = x must raise KeyError in restricted code.
    _write_.__setitem__ now checks for underscore-prefixed keys consistently
    with __setattr__.
    """
    _raises("d = dict()\nd['__class__'] = 'hacked'", KeyError)


# ---------------------------------------------------------------------------
# moo.sdk must not expose internal framework names
# ---------------------------------------------------------------------------

def test_models_not_in_sdk():
    """
    `from moo.sdk import models` must raise ImportError.
    Django ORM model classes (Object.objects, User.objects, etc.) must not be
    reachable from verb code via the public SDK.
    """
    _raises("from moo.sdk import models", ImportError)


def test_auth_not_in_sdk():
    """
    `from moo.sdk import auth` must raise ImportError.
    auth re-exports Player and User ORM models and must not be verb-accessible.
    """
    _raises("from moo.sdk import auth", ImportError)


def test_tasks_not_in_sdk():
    """
    `from moo.sdk import tasks` must raise ImportError.
    tasks exposes raw Celery task functions that bypass the invoke() permission guards.
    """
    _raises("from moo.sdk import tasks", ImportError)


def test_code_not_in_sdk():
    """
    `from moo.sdk import code` must raise ImportError.
    code exposes ContextManager, providing an indirect path to override_caller()
    even though ContextManager itself is blocked by name.
    """
    _raises("from moo.sdk import code", ImportError)


# ---------------------------------------------------------------------------
# _getitem_ must block underscore keys (read side)
# ---------------------------------------------------------------------------

def test_getitem_underscore_key_blocked():
    """
    Reading d['__class__'] in restricted code must raise KeyError.
    dict() (a C builtin) can construct a mapping with underscore keys without
    going through _write_.__setitem__; _getitem_ must guard the read side too.
    """
    # Build the dict with an underscore key via the C-level dict constructor,
    # bypassing _write_.__setitem__, then attempt to read the key.
    _raises("d = dict([('__class__', 'x')])\nprint(d['__class__'])", KeyError)


def test_getitem_normal_keys_still_work():
    """Normal (non-underscore) key reads must continue to work."""
    printed = _exec("d = dict(a=1)\nprint(d['a'])")
    assert printed == [1]


# ---------------------------------------------------------------------------
# str.format() / str.format_map() must not be accessible
# ---------------------------------------------------------------------------

def test_str_format_dunder_blocked():
    """
    str.format() is blocked to prevent C-level dunder traversal.
    '{0.__class__}'.format(obj) bypasses _getattr_ entirely because Python's
    format engine resolves attribute chains using the real C-level getattr.
    Blocking access to .format on string instances closes this vector.
    """
    _raises("print('{0.__class__}'.format('hello'))", AttributeError)


def test_str_format_map_dunder_blocked():
    """str.format_map() is blocked for the same reason as str.format()."""
    _raises("print('{key}'.format_map({'key': 'ok'}))", AttributeError)


def test_str_format_blocked_even_via_variable():
    """
    The format string can be constructed at runtime to defeat static scanning.
    The block must be on the .format attribute itself, not on the string content.
    """
    _raises("fmt = '{0.' + '__class__' + '}'\nprint(fmt.format('hello'))", AttributeError)


def test_str_normal_methods_still_work():
    """Blocking .format must not affect other string methods."""
    printed = _exec("print('hello'.upper())")
    assert printed == ["HELLO"]
    printed = _exec("print('a,b'.split(','))")
    assert printed == [["a", "b"]]


def test_str_replace_still_works():
    """
    str.replace() is the safe substitution method used by message verbs.
    It must remain accessible.
    """
    printed = _exec("print('hello {name}'.replace('{name}', 'world'))")
    assert printed == ["hello world"]


# ---------------------------------------------------------------------------
# Verb.save() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_requires_write_permission(t_init, t_wizard):
    """
    A non-wizard with only read access must not be able to overwrite verb code
    by getting a Verb model instance and calling .save() directly.
    Verb.save() now calls can_caller("write", self) for updates.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    # create a target object owned by wizard, with a verb on it
    with _ctx(t_wizard):
        target = create("target_obj")
        target.add_verb("secret_verb", code='print("original")')

    # create a plain caller that has read but not write on target
    with _ctx(t_wizard):
        plain = create("plain_caller")
        target.allow(plain, "read")

    verb = target.get_verb("secret_verb")
    with _ctx(plain):
        verb.code = "print('hacked')"
        with pytest.raises((PermissionError, AccessError)):
            verb.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_allowed_for_owner(t_init, t_wizard):
    """The owner of an object can still save changes to a verb on it."""
    from moo.sdk import create

    with _ctx(t_wizard):
        target = create("target_obj2")
        target.add_verb("a_verb", code='print("v1")')

    verb = target.get_verb("a_verb")
    with _ctx(t_wizard):
        verb.code = 'print("v2")'
        verb.save()  # must not raise

    verb.refresh_from_db()
    assert verb.code == 'print("v2")'


# ---------------------------------------------------------------------------
# Property.save() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_save_requires_write_permission(t_init, t_wizard):
    """
    A non-wizard with read access must not be able to overwrite a property value
    by obtaining the Property model instance via obj.properties and calling .save().
    Property.save() now calls can_caller("write", self.origin) for updates.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("prop_target")
        target.set_property("secret", "original_value")

    with _ctx(t_wizard):
        plain = create("plain_caller2")
        target.allow(plain, "read")

    prop = target.properties.filter(name="secret").first()
    assert prop is not None
    with _ctx(plain):
        prop.value = '"hacked"'
        with pytest.raises((PermissionError, AccessError)):
            prop.save()


# ---------------------------------------------------------------------------
# Object.delete() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_delete_requires_write_permission(t_init, t_wizard):
    """
    A non-wizard with read access must not be able to delete an arbitrary object.
    Object.delete() now calls can_caller("write", self) before proceeding.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("delete_target")

    with _ctx(t_wizard):
        plain = create("plain_caller3")
        target.allow(plain, "read")

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            target.delete()

    # object must still exist
    target.refresh_from_db()
    assert target.pk is not None


# ---------------------------------------------------------------------------
# Known gap: dict.update() + dict.get() bypass _write_/__getitem__ guards
# ---------------------------------------------------------------------------

def test_dict_update_bypasses_write_guard():
    """
    dict.update({'__class__': x}) inserts underscore keys at C level,
    bypassing _write_.__setitem__. The key can then be retrieved via
    dict.get() or .items()/.values(), bypassing _getitem_.

    This is a known policy gap. dict subclassing would be needed to close it
    fully; for now this test documents the inconsistency.
    """
    # _write_.__setitem__ blocks this:
    _raises("d = {}\nd['__class__'] = 'x'", KeyError)
    # but dict.update() slips through at C level:
    printed = _exec("d = {}\nd.update({'__class__': 'gap'})\nprint(d.get('__class__'))")
    assert printed == ["gap"], "Known gap: dict.update() bypasses _write_.__setitem__"


# ---------------------------------------------------------------------------
# QuerySet.model must not expose raw ORM
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_model_exposes_orm_via_parents(t_init: Object, t_wizard: Object):
    """
    QuerySet.model is blocked by get_protected_attribute and safe_getattr.
    obj.parents.all().model raises AttributeError in verb code, closing the
    raw ORM access path via RelatedManagers.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
cls = obj.parents.all().model
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# Property.value must enforce read permission in verb code
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_read_bypasses_permission_via_relatedmanager(t_init: Object, t_wizard: Object):
    """
    get_protected_attribute and safe_getattr enforce can_caller('read') when
    verb code accesses prop.value. Since all verbs run inside RestrictedPython,
    this guard fires on any prop.value access in verb code by a non-privileged caller.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("prop_read_bypass_target")
        target.set_property("confidential", "top_secret_value")
        plain = create("prop_read_bypass_plain")
        prop = target.properties.filter(name="confidential").first()
        prop.deny(plain, "read")

    prop = target.properties.filter(name="confidential").first()
    assert prop is not None

    # In restricted verb code, a non-privileged caller denied read cannot access prop.value.
    with _ctx(plain):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["prop"] = prop
        with pytest.raises((PermissionError, AccessError)):
            code.r_exec("_ = prop.value", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_read_allowed_for_owner(t_init: Object, t_wizard: Object):
    """The owner's context can still read Property.value."""
    from moo.sdk import create

    with _ctx(t_wizard):
        target = create("prop_owner_read_target")
        target.set_property("public", "expected_value")

    prop = target.properties.filter(name="public").first()
    assert prop is not None
    with _ctx(t_wizard):
        assert "expected_value" in prop.value


# ---------------------------------------------------------------------------
# Verb.__call__() must check execute permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_direct_call_bypasses_execute_permission(t_init: Object, t_wizard: Object):
    """
    Verb.__call__() checks can_caller('execute', self) when an active session
    is present. When execute is explicitly denied for a caller, the check
    raises AccessError instead of running the verb.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("verb_exec_bypass_target")
        target.add_verb("privileged_verb", code='print("privileged ran")')
        plain = create("verb_exec_bypass_plain")
        verb_obj = target.verbs.filter(names__name="privileged_verb").first()
        verb_obj.deny(plain, "execute")

    verb_obj = target.verbs.filter(names__name="privileged_verb").first()
    assert verb_obj is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb_obj(target, None, None)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_passthrough_still_works_after_execute_check(t_init: Object, t_wizard: Object):
    """
    passthrough() must not be blocked by the execute check in Verb.__call__().
    It passes _bypass_execute_check=True so the parent verb call skips the
    redundant permission check.
    """
    from moo.sdk import create

    with _ctx(t_wizard):
        parent = create("passthrough_parent")
        parent.add_verb("greet", code='print("hello from parent")')
        child = create("passthrough_child", parents=[parent])
        child.add_verb("greet", code='passthrough()')

    printed = []
    with _ctx(t_wizard, printed.append):
        child.invoke_verb("greet")
    assert "hello from parent" in printed


# ---------------------------------------------------------------------------
# ACL rules must not be enumerable without grant permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_acl_enumeration_via_relatedmanager(t_init: Object, t_wizard: Object):
    """
    get_protected_attribute and safe_getattr check can_caller('grant') before
    returning the acl RelatedManager on AccessibleMixin instances. Since all
    verbs run in RestrictedPython, verb code accessing obj.acl as a non-privileged
    caller gets AccessError instead of the ACL queryset.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("acl_enum_target")
        reader = create("acl_enum_reader")
        target.allow(reader, "read")
        plain = create("acl_enum_plain")

    with _ctx(plain):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["target"] = target
        with pytest.raises((PermissionError, AccessError)):
            code.r_exec("_ = target.acl", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_acl_enumeration_allowed_for_wizard(t_init: Object, t_wizard: Object):
    """A wizard caller can still access obj.acl, since can_caller('grant') always passes for wizards."""
    from moo.sdk import create

    with _ctx(t_wizard):
        target = create("acl_wizard_target")
        reader = create("acl_wizard_reader")
        target.allow(reader, "read")

    with _ctx(t_wizard):
        entries = list(target.acl.all())
    assert len(entries) > 0


# ---------------------------------------------------------------------------
# context.caller_stack items expose previous caller references (known info disclosure)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="info disclosure only — not scheduled for remediation")
def test_caller_stack_previous_caller_reference_accessible():
    """
    Known gap (information disclosure): context.caller_stack returns a copy of
    the live stack (preventing mutation), but each frame dict contains
    'previous_caller' — a live Object reference. Verb code can read this via
    frame.get('previous_caller') since 'previous_caller' has no underscore
    prefix and dict.get() bypasses _getitem_.

    In a scenario where a wizard verb uses set_task_perms(plain) to run as
    plain, the inner verb sees the wizard Object on the caller stack and can
    call methods like is_wizard() on it. This is information disclosure; it
    does not allow privilege escalation because context.caller is a read-only
    data descriptor that cannot be overwritten.
    """
    wizard_caller = _mock(is_wizard=True)
    non_wizard = _mock(is_wizard=False)

    with _ctx(wizard_caller):
        code.ContextManager.override_caller(non_wizard)
        stack = code.ContextManager.get("caller_stack")
        assert len(stack) == 1
        frame = stack[0]
        # 'previous_caller' has no underscore — _getitem_ does not block it
        prev = frame.get("previous_caller")
        assert prev is wizard_caller, (
            "Known gap: previous_caller is readable from caller_stack copy"
        )
        code.ContextManager.pop_caller()


# ---------------------------------------------------------------------------
# moo.sdk module attribute access
# ---------------------------------------------------------------------------

def test_sdk_contextmanager_blocked_via_module_attribute():
    """
    ContextManager is imported as _ContextManager (underscore alias) in moo/sdk.py.
    Accessing it as `sdk.ContextManager` is blocked because BLOCKED_IMPORTS contains
    'ContextManager' for 'moo.sdk', and the ModuleType guard in get_protected_attribute
    enforces BLOCKED_IMPORTS for attribute-access paths too.
    """
    _raises(
        "import moo.sdk as sdk\nx = sdk.ContextManager",
        AttributeError,
    )


def test_sdk_module_traversal_to_core_blocked():
    """
    `import moo.sdk` (bare, no 'as') binds the top-level `moo` package.
    The ModuleType guard in get_protected_attribute blocks attribute access to any
    submodule whose name is not in ALLOWED_MODULES/WIZARD_ALLOWED_MODULES, so
    `moo.core` raises AttributeError before the ORM is reachable.
    """
    _raises(
        "import moo.sdk\nx = moo.core",
        AttributeError,
    )


# ---------------------------------------------------------------------------
# QuerySet mutation methods must be blocked
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_update_bypasses_verb_save_permission(t_init: Object, t_wizard: Object):
    """
    QuerySet.update() issues SQL UPDATE directly, bypassing Verb.save() permission
    checks. The guard blocks 'update' on QuerySet/BaseManager instances.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
obj.verbs.filter(names__name='look').update(code='print("pwned")')
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_delete_bypasses_permission(t_init: Object, t_wizard: Object):
    """
    QuerySet.delete() issues SQL DELETE directly, bypassing model-level permission
    checks. The guard blocks 'delete' on QuerySet/BaseManager instances.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
obj.verbs.all().delete()
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# QuerySet.values() must not bypass the Property.value guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_values_bypasses_property_value_guard(t_init: Object, t_wizard: Object):
    """
    QuerySet.values() returns plain dicts whose 'value' key is not a Property instance,
    so the isinstance(obj, Property) guard in get_protected_attribute never fires.
    The guard now blocks 'values' on QuerySet/BaseManager.
    """
    from moo.core import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("values_guard_target")
        target.set_property("secret", "top_secret")
        plain = create("values_guard_plain")
        prop = target.properties.filter(name="secret").first()
        prop.deny(plain, "read")

    src = """
from moo.sdk import lookup
obj = lookup(%d)
rows = list(obj.properties.all().values('name', 'value'))
""" % target.pk

    with _ctx(plain):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# RelatedManager.create() must respect write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_relatedmanager_create_bypasses_add_verb_permission(t_init: Object, t_wizard: Object):
    """
    RelatedManager.create() routes directly to Verb.save() with pk=None, which
    previously skipped the write-permission check. The guard now blocks 'create'
    on QuerySet/BaseManager, and Verb.save() also checks permission for creates.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
obj.verbs.create(code='print("injected")')
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# ManyToMany parent manipulation must be blocked
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_m2m_parents_add_blocked(t_init: Object, t_wizard: Object):
    """
    ManyToManyField.add() issues SQL directly without going through Object.save(),
    bypassing ACL checks. The guard blocks 'add' on BaseManager instances.
    """
    from moo.core import create

    with _ctx(t_wizard):
        target = create("m2m_add_target")
        extra_parent = create("m2m_add_parent")

    src = """
from moo.sdk import lookup
target = lookup(%d)
extra = lookup(%d)
target.parents.add(extra)
""" % (target.pk, extra_parent.pk)

    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


# ---------------------------------------------------------------------------
# VerbName.save() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verbname_save_requires_write_permission(t_init: Object, t_wizard: Object):
    """
    VerbName.save() previously had no permission check. A non-wizard with only
    read access could rename a verb by fetching its VerbName via verb.names.all()
    and calling .save() on it directly. VerbName.save() now calls
    verb.can_caller('write', verb) before delegating to super().save().
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("verbname_save_target")
        target.add_verb("secret_verb", code='print("hi")')
        plain = create("verbname_save_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="secret_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with _ctx(plain):
        vname.name = "hijacked"
        with pytest.raises((PermissionError, AccessError)):
            vname.save()

    # Name must be unchanged.
    vname.refresh_from_db()
    assert vname.name == "secret_verb"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verbname_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """
    VerbName.delete() previously had no permission check. A non-wizard with read
    access could remove a verb's names (breaking dispatch) by calling .delete()
    on a VerbName instance. VerbName.delete() now calls can_caller('write', verb).
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("verbname_del_target")
        target.add_verb("named_verb", code='print("hi")')
        plain = create("verbname_del_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="named_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            vname.delete()

    # VerbName must still exist.
    assert verb.names.filter(name="named_verb").exists()


# ---------------------------------------------------------------------------
# Alias.delete() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_alias_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """
    Alias.save() was already permission-checked, but Alias.delete() was not.
    A non-wizard with read access could delete an object's alias (altering how
    it is found by lookup()) by calling .delete() on an Alias instance.
    Alias.delete() now calls can_caller('write', self.object).
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.object import Alias

    with _ctx(t_wizard):
        target = create("alias_del_target")
        target.add_alias("my_alias")
        plain = create("alias_del_plain")
        target.allow(plain, "read")

    alias = Alias.objects.filter(object=target, alias="my_alias").first()
    assert alias is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            alias.delete()

    # Alias must still exist.
    assert Alias.objects.filter(object=target, alias="my_alias").exists()


# ---------------------------------------------------------------------------
# Verb.reload() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_reload_requires_write_permission(t_init: Object, t_wizard: Object):
    """
    Verb.reload() previously had no permission check. A non-wizard with read
    access could call verb.reload() to trigger a repo fetch and overwrite verb
    code. Verb.reload() now calls origin.can_caller('write', self) first.
    The check fires even when repo/filename are None, so AccessError is raised
    before the RuntimeError for missing repo config.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("verb_reload_target")
        target.add_verb("reload_verb", code='print("original")')
        plain = create("verb_reload_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="reload_verb").first()
    assert verb is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.reload()


# ---------------------------------------------------------------------------
# Verb.invoked_object / invoked_name must be inaccessible
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_write_blocked(t_init: Object, t_wizard: Object):
    """
    Verb.invoked_object is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting the 'this' context to an arbitrary object
    before calling the verb.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        target = create("invoked_obj_write_target")
        target.add_verb("test_verb", code='print("ok")')
        other = create("invoked_obj_other")

    verb_obj = target.verbs.filter(names__name="test_verb").first()
    assert verb_obj is not None

    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        g["other"] = other
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("verb_obj.invoked_object = other", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_name_write_blocked(t_init: Object, t_wizard: Object):
    """
    Verb.invoked_name is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting passthrough() to an arbitrary verb name.
    RestrictedPython rejects _-prefixed attribute names at compile time
    (code.code is None), so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with _ctx(t_wizard):
        target = create("invoked_name_write_target")
        target.add_verb("test_verb2", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb2").first()
    assert verb_obj is not None

    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("verb_obj.invoked_name = 'hijacked'", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_read_blocked(t_init: Object, t_wizard: Object):
    """
    Verb.invoked_object is underscore-prefixed; get_protected_attribute must
    block read access from verb code, preventing information disclosure about
    the dispatch target. RestrictedPython rejects _-prefixed attribute names
    at compile time, so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with _ctx(t_wizard):
        target = create("invoked_obj_read_target")
        target.add_verb("test_verb3", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb3").first()
    verb_obj.invoked_object = target

    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("_ = verb_obj.invoked_object", {}, g)


# ---------------------------------------------------------------------------
# Access.save() / Access.delete() must require grant permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_save_requires_grant(t_init: Object, t_wizard: Object):
    """
    Access.save() previously had no permission check. A non-wizard with grant
    on their own object could obtain an Access row, reassign its object FK to
    a wizard-owned object, then call save() to inject an ACL entry without
    having grant on the target. Access.save() now calls can_caller("grant")
    against the entity the row belongs to.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        attacker = create("acl_save_attacker")
        target = create("acl_save_target")
        attacker.allow(attacker, "grant")
        attacker.allow("everyone", "read")

    access = attacker.acl.filter(group="everyone").first()
    assert access is not None

    access.object = target

    with _ctx(attacker):
        with pytest.raises((PermissionError, AccessError)):
            access.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_save_new_entry_requires_grant(t_init: Object, t_wizard: Object):
    """
    Creating a new Access row directly (bypassing allow()/deny()) must require
    grant on the target entity. Previously Access.save() had no check, so any
    caller could insert arbitrary ACL rows.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.acl import Access, Permission

    with _ctx(t_wizard):
        plain = create("acl_new_plain")
        protected = create("acl_new_protected")

    perm = Permission.objects.get(name="read")

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            Access(
                object=protected,
                rule="allow",
                permission=perm,
                type="group",
                group="everyone",
            ).save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_delete_requires_grant(t_init: Object, t_wizard: Object):
    """
    Access.delete() previously had no permission check. Without it an attacker
    could delete ACL entries on objects they have no grant over. Access.delete()
    now calls can_caller("grant") on the entity the row belongs to.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with _ctx(t_wizard):
        plain = create("acl_del_plain")
        protected = create("acl_del_protected")
        protected.allow("everyone", "read")

    access = protected.acl.filter(group="everyone").first()
    assert access is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            access.delete()

    assert protected.acl.filter(group="everyone").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_repository_save_requires_wizard(t_init: Object, t_wizard: Object):
    """
    Repository.save() previously had no permission check. A non-wizard with
    read access to a verb could reach verb.repo and overwrite the URL,
    redirecting future verb.reload() fetches to an attacker-controlled source.
    Repository.save() now raises AccessError for non-wizard callers.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.verb import Repository

    with _ctx(t_wizard):
        plain = create("repo_save_plain")
        target = create("repo_save_target")
        repo = Repository(slug="test-repo", url="https://gitlab.com/test/repo.git", prefix="verbs/")
        repo.save()
        target.add_verb("repo_verb", code='print("ok")', repo=repo, filename="verbs/repo_verb.py")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="repo_verb").first()
    assert verb is not None
    assert verb.repo is not None

    with _ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.repo.url = "https://attacker.example.com/evil.git"
            verb.repo.save()
