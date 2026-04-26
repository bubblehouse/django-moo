# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: Object model permission checks.

Covers Object.delete write enforcement, Object.remove_parent write
enforcement, the _original_owner / _original_location entrust-bypass
defenses, and the wizard-ORM queryset-mutation guard.
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import mock_caller, raises_in_verb, ctx

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
        with pytest.raises((AttributeError, TypeError, SyntaxError)):
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
        with pytest.raises((AttributeError, TypeError, SyntaxError)):
            code.r_exec("obj._original_location = room.pk", {}, g)


# ---------------------------------------------------------------------------
# Object.remove_parent() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_remove_parent_works(t_init: Object, t_wizard: Object):
    """Wizard can remove a parent from an object they own."""
    from moo.sdk import create

    with ctx(t_wizard):
        base = create("remove_parent_base")
        child = create("remove_parent_child")
        child.add_parent(base)

    assert child.parents.filter(pk=base.pk).exists()

    with ctx(t_wizard):
        child.remove_parent(base)

    assert not child.parents.filter(pk=base.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_remove_parent_requires_write(t_init: Object, t_wizard: Object):
    """

    remove_parent() calls can_caller("write") on the child object before
    removing the parent. A caller with only read access must not be able to
    strip parents from an object, which could alter verb dispatch and break
    permission inheritance.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        base = create("remove_parent_req_base")
        child = create("remove_parent_req_child")
        child.add_parent(base)
        plain = create("remove_parent_req_plain")
        child.allow(plain, "read")

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            child.remove_parent(base)

    assert child.parents.filter(pk=base.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_add_parent_regression(t_init: Object, t_wizard: Object):
    """add_parent() still works correctly after remove_parent() was added — regression."""
    from moo.sdk import create

    with ctx(t_wizard):
        base = create("add_parent_reg_base")
        child = create("add_parent_reg_child")
        child.add_parent(base)

    assert child.parents.filter(pk=base.pk).exists()


# ---------------------------------------------------------------------------
# Wizard ORM access via WIZARD_ALLOWED_MODULES
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_wizard_allowed_modules_queryset_mutations_still_blocked(t_init: Object, t_wizard: Object):
    """

    WIZARD_ALLOWED_MODULES includes moo.core.models, giving wizard verb code
    access to Object, Verb, Property, User, Player, and other model classes for
    debugging purposes.  Wizards are system administrators; this is intentional.

    QuerySet mutation methods (update, delete, bulk_create, etc.) remain blocked
    by the _QUERYSET_ALLOWED guard in code.py regardless of wizard status.
    Wizards cannot use a direct QuerySet .update() call to bypass model-level
    permission checks.
    """
    raises_in_verb(
        "from moo.core.models import Object\nObject.objects.filter(pk=1).update(name='hacked')",
        AttributeError,
        caller=mock_caller(is_wizard=True),
    )
