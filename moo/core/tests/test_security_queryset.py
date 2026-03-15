# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: QuerySet / RelatedManager access controls.

Covers: QuerySet.model raw ORM path, bulk mutation methods (update/delete/
values/create), ManyToMany parent manipulation, Property.value read guard,
Verb.__call__ execute check, ACL enumeration guard, select_related safety
(passes 6, 7, 8, 14).
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import ctx


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
    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)


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
    with ctx(t_wizard):
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
    with ctx(t_wizard):
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

    with ctx(t_wizard):
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

    with ctx(plain):
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
    with ctx(t_wizard):
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

    with ctx(t_wizard):
        target = create("m2m_add_target")
        extra_parent = create("m2m_add_parent")

    src = """
from moo.sdk import lookup
target = lookup(%d)
extra = lookup(%d)
target.parents.add(extra)
""" % (target.pk, extra_parent.pk)

    with ctx(t_wizard):
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

    with ctx(t_wizard):
        target = create("prop_read_bypass_target")
        target.set_property("confidential", "top_secret_value")
        plain = create("prop_read_bypass_plain")
        prop = target.properties.filter(name="confidential").first()
        prop.deny(plain, "read")

    prop = target.properties.filter(name="confidential").first()
    assert prop is not None

    with ctx(plain):
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

    with ctx(t_wizard):
        target = create("prop_owner_read_target")
        target.set_property("public", "expected_value")

    prop = target.properties.filter(name="public").first()
    assert prop is not None
    with ctx(t_wizard):
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

    with ctx(t_wizard):
        target = create("verb_exec_bypass_target")
        target.add_verb("privileged_verb", code='print("privileged ran")')
        plain = create("verb_exec_bypass_plain")
        verb_obj = target.verbs.filter(names__name="privileged_verb").first()
        verb_obj.deny(plain, "execute")

    verb_obj = target.verbs.filter(names__name="privileged_verb").first()
    assert verb_obj is not None

    with ctx(plain):
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

    with ctx(t_wizard):
        parent = create("passthrough_parent")
        parent.add_verb("greet", code='print("hello from parent")')
        child = create("passthrough_child", parents=[parent])
        child.add_verb("greet", code='passthrough()')

    printed = []
    with ctx(t_wizard, printed.append):
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

    with ctx(t_wizard):
        target = create("acl_enum_target")
        reader = create("acl_enum_reader")
        target.allow(reader, "read")
        plain = create("acl_enum_plain")

    with ctx(plain):
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

    with ctx(t_wizard):
        target = create("acl_wizard_target")
        reader = create("acl_wizard_reader")
        target.allow(reader, "read")

    with ctx(t_wizard):
        entries = list(target.acl.all())
    assert len(entries) > 0


# ---------------------------------------------------------------------------
# select_related() safety (pass 14)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_select_related_does_not_expose_new_attack_surface(t_init: Object, t_wizard: Object):
    """

    select_related() is in _QUERYSET_ALLOWED and is actively used by verb code
    (e.g. at_show.py).  It returns a QuerySet of the same model type; the
    instances it produces still go through get_protected_attribute when accessed.
    Confirming it does not open a new ORM or dunder access path.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
verbs = list(obj.verbs.select_related('owner').all())
print(len(verbs) >= 0)
"""
    printed = []
    with ctx(t_wizard, printed.append):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        code.r_exec(src, {}, g)
    assert printed == [True]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_select_related_cannot_reach_queryset_model_attr(t_init: Object, t_wizard: Object):
    """

    select_related() returns a QuerySet.  The QuerySet.model attribute is blocked
    by the _QUERYSET_ALLOWED guard, so an attacker cannot use select_related() as
    a stepping stone to raw ORM access via the model class.
    """
    src = """
from moo.sdk import lookup
obj = lookup(1)
cls = obj.verbs.select_related('owner').model
"""
    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        with pytest.raises(AttributeError):
            code.r_exec(src, {}, g)
