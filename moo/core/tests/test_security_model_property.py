# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: Property model permission checks.

Covers Property.save / .delete write enforcement, the entrust requirement
when changing a property's owner, and set_protected_attribute() ACL
enforcement (the Object.__dict__ shadowing attack).
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import ctx

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

    with ctx(t_wizard):
        target = create("prop_target")
        target.set_property("secret", "original_value")

    with ctx(t_wizard):
        plain = create("plain_caller2")
        target.allow(plain, "read")

    prop = target.properties.filter(name="secret").first()
    assert prop is not None
    with ctx(plain):
        prop.value = '"hacked"'
        with pytest.raises((PermissionError, AccessError)):
            prop.save()


# ---------------------------------------------------------------------------
# Property.delete() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    Property.delete() previously had no permission check. A non-wizard with
    read access could get a Property instance via obj.properties.filter(...).first()
    and call .delete() to destroy the property. Property.delete() now calls
    origin.can_caller("write", self) before delegating to super().delete().
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("prop_del_target")
        target.set_property("critical_prop", "important_value")
        plain = create("prop_del_plain")
        target.allow(plain, "read")

    prop = target.properties.filter(name="critical_prop").first()
    assert prop is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            prop.delete()

    assert target.properties.filter(name="critical_prop").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_delete_allowed_for_owner(t_init: Object, t_wizard: Object):
    """The owner can delete a property on their own object."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("prop_del_owner_target")
        target.set_property("deletable_prop", "bye")

    prop = target.properties.filter(name="deletable_prop").first()
    assert prop is not None

    with ctx(t_wizard):
        prop.delete()


# ---------------------------------------------------------------------------
# set_protected_attribute must enforce write ACL, not just underscore blocking
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_set_protected_attribute_shadows_moo_property_without_acl(t_init: Object, t_wizard: Object):
    """

    set_protected_attribute() only checks for underscore prefixes before calling
    setattr(). For Object instances, this sets a Python __dict__ entry that
    shadows a DB-backed MOO property — without any can_caller("write") check.

    Attack path: verb code does ``target.secret = "injected"``. RestrictedPython
    transforms that to ``_write_(target).__setattr__('secret', 'injected')``,
    which calls ``set_protected_attribute(target, 'secret', 'injected')``,
    which calls ``setattr(target, 'secret', 'injected')``. Since Object has no
    custom __setattr__, this lands directly in target.__dict__. Python's MRO
    finds __dict__ values before calling __getattr__, so subsequent reads return
    the injected value without ever passing through get_property() or its
    can_caller("read") check.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("shadow_target")
        target.set_property("secret_flag", False)
        plain = create("shadow_plain")
        target.allow(plain, "read")

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            target.set_property("secret_flag", True)

    with ctx(plain):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["target"] = target
        with pytest.raises((PermissionError, AttributeError, AccessError)):
            code.r_exec("target.secret_flag = True", {}, g)

    target.refresh_from_db()
    assert target.get_property("secret_flag") is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_set_protected_attribute_on_system_object_requires_write(t_init: Object, t_wizard: Object):
    """

    The system object (pk=1) is passed as ``_`` to every verb. Without an ACL
    check in set_protected_attribute, non-wizard verb code can shadow its MOO
    properties in-memory (e.g. ``_.root_class = evil_obj``), affecting any SDK
    code that reuses the cached system object within the same session.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        plain = create("system_shadow_plain")

    system = Object.objects.get(pk=1)

    with ctx(plain):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["system"] = system
        with pytest.raises((PermissionError, AttributeError)):
            code.r_exec("system.root_class = system", {}, g)


# ---------------------------------------------------------------------------
# Property.save() must require entrust to change owner
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_owner_change_requires_entrust(t_init: Object, t_wizard: Object):
    """

    Property.owner is documented as requiring `entrust` permission to change,
    but Property.save() previously only checked `write`. A verb author with write
    access to an object could reassign a property's owner to any arbitrary object
    by fetching the Property instance and calling .save() with a new owner set.
    Property.save() now also calls can_caller("entrust") when owner_id changes.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("prop_entrust_target")
        target.set_property("guarded", "value")
        writer = create("prop_entrust_writer")
        new_owner = create("prop_entrust_new_owner")
        target.allow(writer, "write")

    prop = target.properties.filter(name="guarded").first()
    assert prop is not None

    prop_reloaded = prop.__class__.objects.get(pk=prop.pk)
    prop_reloaded.owner = new_owner

    with ctx(writer):
        with pytest.raises((PermissionError, AccessError)):
            prop_reloaded.save()

    prop.refresh_from_db()
    assert prop.owner == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_owner_change_allowed_with_entrust(t_init: Object, t_wizard: Object):
    """Wizard (who has entrust on everything) can transfer property ownership."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("prop_entrust_ok_target")
        target.set_property("transferable", "value")
        new_owner = create("prop_entrust_ok_new_owner")

    prop = target.properties.filter(name="transferable").first()
    assert prop is not None

    prop_reloaded = prop.__class__.objects.get(pk=prop.pk)
    prop_reloaded.owner = new_owner

    with ctx(t_wizard):
        prop_reloaded.save()

    prop.refresh_from_db()
    assert prop.owner == new_owner


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_change_does_not_require_entrust(t_init: Object, t_wizard: Object):
    """Changing a property's value (without changing owner) still only needs write — regression."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("prop_value_change_target")
        target.set_property("editable", "original")
        writer = create("prop_value_change_writer")

    prop = target.properties.filter(name="editable").first()
    assert prop is not None

    with ctx(t_wizard):
        prop.allow(writer, "write")

    prop_reloaded = prop.__class__.objects.get(pk=prop.pk)
    prop_reloaded.value = '"updated"'

    with ctx(writer):
        prop_reloaded.save()

    prop.refresh_from_db()
    assert prop.value == '"updated"'
