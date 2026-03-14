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

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_orm_access_via_getattr_chain(t_init: Object, t_wizard: Object):
    """
    An attacker cannot reach Object.objects by walking __class__ → objects.
    getattr(obj, '__class__') is blocked, so the chain never starts.
    """
    src = """
from moo.core import lookup
obj = lookup(1)
cls = getattr(obj, '__class__')
mgr = getattr(cls, 'objects')
print(mgr.count())
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


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
    ContextManager is in BLOCKED_IMPORTS for moo.core.
    Verb code must not be able to call override_caller() to impersonate another player.
    """
    _raises("from moo.core import ContextManager", ImportError)


# ---------------------------------------------------------------------------
# set_task_perms must require wizard (regression guard)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_set_task_perms_requires_wizard(t_init: Object, t_wizard: Object):
    """
    set_task_perms() raises UserError when called by a non-wizard.
    This is already enforced; test guards against regression.
    """
    from moo.core import set_task_perms
    from moo.core.exceptions import UserError

    # Create a plain (non-wizard) object to act as caller
    from moo.core import create
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
    _raises("from moo.core import _publish_to_player", (ImportError, TypeError))


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
    from moo.core import invoke
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
    from moo.core import invoke
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
    from moo.core import invoke

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
    from moo.core import context

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
    _raises("from moo.core import context\ncontext.caller = None", AttributeError)


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


def test_string_formatter_bypass_blocked():
    """
    Confirming that the string.Formatter bypass path is closed end-to-end.
    """
    _raises("from string import Formatter", ImportError)


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
    from moo.core import invoke

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
# moo.core submodules must not be importable (ORM access via models)
# ---------------------------------------------------------------------------

def test_models_submodule_not_importable():
    """
    `from moo.core import models` must raise ImportError.
    moo.core.models exposes Django ORM model classes (Object.objects,
    User.objects, etc.) with no permission checks.  'models' is now in
    BLOCKED_IMPORTS for moo.core.
    """
    _raises("from moo.core import models", ImportError)


def test_auth_submodule_not_importable():
    """
    `from moo.core import auth` must raise ImportError.
    moo.core.auth re-exports Player and User ORM models.
    """
    _raises("from moo.core import auth", ImportError)


def test_tasks_submodule_not_importable():
    """
    `from moo.core import tasks` must raise ImportError.
    moo.core.tasks exposes raw Celery task functions that bypass the invoke()
    permission guards.
    """
    _raises("from moo.core import tasks", ImportError)


def test_code_submodule_not_importable():
    """
    `from moo.core import code` must raise ImportError.
    moo.core.code exposes ContextManager, providing an indirect path to
    override_caller() even though ContextManager itself is blocked by name.
    """
    _raises("from moo.core import code", ImportError)


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
    from moo.core import create
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
    from moo.core import create

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
    from moo.core import create
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
    from moo.core import create
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
from moo.core import lookup
obj = lookup(1)
cls = obj.parents.all().model
"""
    with _ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_model_exposes_orm_via_verbs(t_init: Object, t_wizard: Object):
    """
    Same guard via the obj.verbs RelatedManager. Confirms that blocking .model
    on QuerySet instances covers all RelatedManager paths.
    """
    src = """
from moo.core import lookup
obj = lookup(1)
cls = obj.verbs.all().model
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
    from moo.core import create
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
    from moo.core import create

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
    from moo.core import create
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
    from moo.core import create

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
    from moo.core import create
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
    from moo.core import create

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
