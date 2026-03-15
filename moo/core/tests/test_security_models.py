# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: model-level permission checks.

Covers: Verb/Property/Object save/delete, VerbName save/delete, Alias delete,
Verb.reload, Verb._invoked_object/_invoked_name, Access save/delete,
Repository save, set_protected_attribute write ACL, _original_owner/
_original_location tracking fields (passes 5, 8, 9, 10, 11, 12, 13).
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import ctx


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

    with ctx(t_wizard):
        target = create("target_obj")
        target.add_verb("secret_verb", code='print("original")')

    with ctx(t_wizard):
        plain = create("plain_caller")
        target.allow(plain, "read")

    verb = target.get_verb("secret_verb")
    with ctx(plain):
        verb.code = "print('hacked')"
        with pytest.raises((PermissionError, AccessError)):
            verb.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_allowed_for_owner(t_init, t_wizard):
    """The owner of an object can still save changes to a verb on it."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("target_obj2")
        target.add_verb("a_verb", code='print("v1")')

    verb = target.get_verb("a_verb")
    with ctx(t_wizard):
        verb.code = 'print("v2")'
        verb.save()

    verb.refresh_from_db()
    assert verb.code == 'print("v2")'


# ---------------------------------------------------------------------------
# Verb.delete() must require write permission
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    Verb.delete() previously had no permission check. A non-wizard with read
    access could get a Verb instance via obj.verbs.filter(...).first() and call
    .delete() to destroy the verb, breaking dispatch. Verb.delete() now calls
    origin.can_caller("write", self) before delegating to super().delete().
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("verb_del_target")
        target.add_verb("important_verb", code='print("hi")')
        plain = create("verb_del_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="important_verb").first()
    assert verb is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.delete()

    assert target.verbs.filter(names__name="important_verb").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_delete_allowed_for_owner(t_init: Object, t_wizard: Object):
    """The owner can delete a verb on their own object."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("verb_del_owner_target")
        target.add_verb("deletable_verb", code='print("bye")')

    verb = target.verbs.filter(names__name="deletable_verb").first()
    assert verb is not None

    with ctx(t_wizard):
        verb.delete()

    assert not target.verbs.filter(names__name="deletable_verb").exists()


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

    with ctx(t_wizard):
        target = create("delete_target")

    with ctx(t_wizard):
        plain = create("plain_caller3")
        target.allow(plain, "read")

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            target.delete()

    target.refresh_from_db()
    assert target.pk is not None


# ---------------------------------------------------------------------------
# VerbName.save() / VerbName.delete() must require write permission
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

    with ctx(t_wizard):
        target = create("verbname_save_target")
        target.add_verb("secret_verb", code='print("hi")')
        plain = create("verbname_save_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="secret_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with ctx(plain):
        vname.name = "hijacked"
        with pytest.raises((PermissionError, AccessError)):
            vname.save()

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

    with ctx(t_wizard):
        target = create("verbname_del_target")
        target.add_verb("named_verb", code='print("hi")')
        plain = create("verbname_del_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="named_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            vname.delete()

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

    with ctx(t_wizard):
        target = create("alias_del_target")
        target.add_alias("my_alias")
        plain = create("alias_del_plain")
        target.allow(plain, "read")

    alias = Alias.objects.filter(object=target, alias="my_alias").first()
    assert alias is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            alias.delete()

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

    with ctx(t_wizard):
        target = create("verb_reload_target")
        target.add_verb("reload_verb", code='print("original")')
        plain = create("verb_reload_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="reload_verb").first()
    assert verb is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.reload()


# ---------------------------------------------------------------------------
# Verb._invoked_object / _invoked_name must be inaccessible from sandbox
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_write_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_object is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting the 'this' context to an arbitrary object
    before calling the verb.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_obj_write_target")
        target.add_verb("test_verb", code='print("ok")')
        other = create("invoked_obj_other")

    verb_obj = target.verbs.filter(names__name="test_verb").first()
    assert verb_obj is not None

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        g["other"] = other
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("verb_obj._invoked_object = other", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_name_write_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_name is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting passthrough() to an arbitrary verb name.
    RestrictedPython rejects _-prefixed attribute names at compile time
    (code.code is None), so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_name_write_target")
        target.add_verb("test_verb2", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb2").first()
    assert verb_obj is not None

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("verb_obj._invoked_name = 'hijacked'", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_read_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_object is underscore-prefixed; get_protected_attribute must
    block read access from verb code, preventing information disclosure about
    the dispatch target. RestrictedPython rejects _-prefixed attribute names
    at compile time, so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_obj_read_target")
        target.add_verb("test_verb3", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb3").first()
    verb_obj._invoked_object = target

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("_ = verb_obj._invoked_object", {}, g)


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

    with ctx(t_wizard):
        attacker = create("acl_save_attacker")
        target = create("acl_save_target")
        attacker.allow(attacker, "grant")
        attacker.allow("everyone", "read")

    access = attacker.acl.filter(group="everyone").first()
    assert access is not None

    access.object = target

    with ctx(attacker):
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

    with ctx(t_wizard):
        plain = create("acl_new_plain")
        protected = create("acl_new_protected")

    perm = Permission.objects.get(name="read")

    with ctx(plain):
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

    with ctx(t_wizard):
        plain = create("acl_del_plain")
        protected = create("acl_del_protected")
        protected.allow("everyone", "read")

    access = protected.acl.filter(group="everyone").first()
    assert access is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            access.delete()

    assert protected.acl.filter(group="everyone").exists()


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
# Repository.save() must require wizard
# ---------------------------------------------------------------------------

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

    with ctx(t_wizard):
        plain = create("repo_save_plain")
        target = create("repo_save_target")
        repo = Repository(slug="test-repo", url="https://gitlab.com/test/repo.git", prefix="verbs/")
        repo.save()
        target.add_verb("repo_verb", code='print("ok")', repo=repo, filename="verbs/repo_verb.py")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="repo_verb").first()
    assert verb is not None
    assert verb.repo is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.repo.url = "https://attacker.example.com/evil.git"
            verb.repo.save()


# ---------------------------------------------------------------------------
# _original_owner / _original_location tracking fields must be inaccessible
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_original_owner_write_blocked(t_init: Object, t_wizard: Object):
    """

    Object._original_owner is the pre-save owner snapshot used by Object.save()
    to detect ownership changes and trigger the `entrust` permission check.
    Before this fix, an attacker with `write` access could set
    obj.original_owner = new_owner.pk (no underscore, passes set_protected_attribute)
    then set obj.owner = new_owner and call obj.save(), suppressing the entrust
    check and stealing ownership without entrust permission.

    Fix: renamed to _original_owner (underscore prefix). RestrictedPython and
    set_protected_attribute both block _-prefixed names.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        victim = create("original_owner_victim")
        attacker = create("original_owner_attacker")
        victim.allow(attacker, "write")

    with ctx(attacker):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["victim"] = victim
        g["attacker"] = attacker
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("victim._original_owner = attacker.pk", {}, g)

    victim.refresh_from_db()
    assert victim.owner == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_entrust_check_fires_for_third_party_transfer(t_init: Object, t_wizard: Object):
    """

    A caller with write but not entrust cannot use Object.save() to transfer
    ownership to a THIRD PARTY (one who is not the current caller).  After
    super().save() the new owner is the third party, so the "owners" group check
    still fails for the attacker — triggering AccessError.  The _original_owner
    injection bug would have let sandbox code suppress this check by pre-matching
    the snapshot to the intended new owner; renaming to _original_owner closes it.
    """
    from django.db import transaction
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        victim = create("entrust_3p_victim")
        attacker = create("entrust_3p_attacker")
        third_party = create("entrust_3p_third_party")
        victim.allow(attacker, "write")

    victim_reloaded = victim.__class__.objects.get(pk=victim.pk)
    victim_reloaded.owner = third_party

    with ctx(attacker):
        with pytest.raises((PermissionError, AccessError)):
            with transaction.atomic():
                victim_reloaded.save()

    victim.refresh_from_db()
    assert victim.owner == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_original_location_write_blocked(t_init: Object, t_wizard: Object):
    """

    Object._original_location is the pre-save location snapshot used by Object.save()
    to detect location changes and trigger the `move` permission check plus accept/
    enterfunc/exitfunc logic. An attacker with write access could previously set
    obj.original_location = new_loc.pk to suppress the move check. Fix: renamed to
    _original_location.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        obj = create("original_loc_obj")
        room = create("original_loc_room")
        attacker = create("original_loc_attacker")
        obj.allow(attacker, "write")

    with ctx(attacker):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["obj"] = obj
        g["room"] = room
        with pytest.raises((AttributeError, TypeError)):
            code.r_exec("obj._original_location = room.pk", {}, g)
