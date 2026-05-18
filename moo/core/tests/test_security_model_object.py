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
def test_remove_parent_requires_transmute_and_derive(t_init: Object, t_wizard: Object):
    """

    remove_parent() goes through the m2m_changed signal handler, which
    enforces ``transmute`` on the child and ``derive`` on the parent. A
    caller with only ``read`` access must not be able to strip parents
    from an object, which could alter verb dispatch and break permission
    inheritance.

    Note: as of the granular-ACL pass, the helper no longer requires
    ``write`` on the child — ``transmute``+``derive`` are sufficient,
    matching the signal handler's own checks.
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
def test_remove_parent_with_transmute_and_derive_only(t_init: Object, t_wizard: Object):
    """

    A caller with ``transmute`` on the child and ``derive`` on the parent
    (but no ``write`` on either) can successfully remove the parent.
    Confirms the granular-ACL loosening of ``add_parent``/``remove_parent``.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        base = create("granular_remove_base")
        child = create("granular_remove_child")
        child.add_parent(base)
        plain = create("granular_remove_caller")
        child.allow(plain, "transmute")
        base.allow(plain, "derive")

    with ctx(plain):
        child.remove_parent(base)

    assert not child.parents.filter(pk=base.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_add_parent_with_transmute_and_derive_only(t_init: Object, t_wizard: Object):
    """

    Mirror of the remove test: ``add_parent`` only requires ``transmute``
    on the child and ``derive`` on the parent.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        base = create("granular_add_base")
        child = create("granular_add_child")
        plain = create("granular_add_caller")
        child.allow(plain, "transmute")
        base.allow(plain, "derive")

    with ctx(plain):
        child.add_parent(base)

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
# Object.save(): granular ACLs replace the unconditional `write` floor
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_save_location_only_requires_move(t_init: Object, t_wizard: Object):
    """

    A caller with ``move`` permission on an object (but not ``write``)
    can change ``location`` and save. Before the granular-ACL pass, the
    unconditional ``write`` check at the top of Object.save() blocked
    every save, making ``move`` effectively unusable for non-owners.
    """
    from moo.sdk import create
    from .utils import add_verb

    with ctx(t_wizard):
        thing = create("move_only_thing")
        dest = create("move_only_dest")
        # add_verb bypasses ACL — give dest an accept verb that always returns True.
        add_verb(dest, "accept", "return True", owner=t_wizard)
        plain = create("move_only_caller")
        thing.allow(plain, "move")

    with ctx(plain):
        thing.location = dest
        thing.save()

    thing.refresh_from_db()
    assert thing.location_id == dest.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_save_name_change_still_requires_write(t_init: Object, t_wizard: Object):
    """

    A caller with ``move`` and ``entrust`` but not ``write`` cannot change
    a non-ACL field like ``name``. The ``write`` check now fires only when
    a non-location/non-owner field changed, but it MUST fire then.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        thing = create("name_change_thing")
        plain = create("name_change_caller")
        thing.allow(plain, "move")
        thing.allow(plain, "entrust")

    with ctx(plain):
        thing.name = "renamed_by_attacker"
        with pytest.raises((PermissionError, AccessError)):
            thing.save()

    thing.refresh_from_db()
    assert thing.name == "name_change_thing"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_save_combined_change_requires_all_relevant_perms(t_init: Object, t_wizard: Object):
    """

    When both ``location`` and a non-ACL field change in the same save,
    both ``move`` AND ``write`` are required. A caller with only ``move``
    cannot smuggle in a name change alongside a relocation.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from .utils import add_verb

    with ctx(t_wizard):
        thing = create("combined_change_thing")
        dest = create("combined_change_dest")
        add_verb(dest, "accept", "return True", owner=t_wizard)
        plain = create("combined_change_caller")
        thing.allow(plain, "move")

    with ctx(plain):
        thing.location = dest
        thing.name = "smuggled_rename"
        with pytest.raises((PermissionError, AccessError)):
            thing.save()

    thing.refresh_from_db()
    assert thing.name == "combined_change_thing"
    assert thing.location_id != dest.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_save_owner_only_requires_entrust(t_init: Object, t_wizard: Object):
    """

    A caller with ``entrust`` on an object (but not ``write``) can transfer
    ownership. Before the granular-ACL pass, ``entrust`` was unreachable —
    the upstream ``write`` check blocked every save first.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        thing = create("entrust_only_thing")
        new_owner = create("entrust_only_new_owner")
        plain = create("entrust_only_caller")
        thing.allow(plain, "entrust")

    with ctx(plain):
        thing.owner = new_owner
        thing.save()

    thing.refresh_from_db()
    assert thing.owner_id == new_owner.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_save_no_change_skips_write_check(t_init: Object, t_wizard: Object):
    """

    Re-saving an object with no field changes does not require ``write``.
    Confirms the conditional fires correctly on the equality check.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        thing = create("no_change_thing")
        plain = create("no_change_caller")
        # Plain has only `read`. With no field changes, save() must succeed
        # because no ACL gate is triggered.
        thing.allow(plain, "read")

    with ctx(plain):
        # Touch nothing; save() should be a no-op as far as ACL is concerned.
        thing.save()

    thing.refresh_from_db()
    assert thing.name == "no_change_thing"


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
