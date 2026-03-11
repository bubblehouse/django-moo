# -*- coding: utf-8 -*-
"""
Tests for moo/core/models/acl.py — Permission, Access, AccessibleMixin.
"""

from django.db import connection

import pytest

from .. import code, create, exceptions, lookup
from ..models import Access, Object, Permission, Player
from ..models.acl import _get_permission_id


def _ctx(wizard):
    return code.ContextManager(wizard, lambda m: None)


# ---------------------------------------------------------------------------
# Permission.__str__
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_permission_str(t_init, t_wizard):
    perm = Permission.objects.get(name="read")
    assert str(perm) == "read"


# ---------------------------------------------------------------------------
# Access.__str__
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_str(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("access str obj")
        obj.allow("everyone", "read")
    rule = Access.objects.filter(object=obj, rule="allow", group="everyone").first()
    s = str(rule)
    assert "allow" in s
    assert "read" in s


# ---------------------------------------------------------------------------
# can_caller with no active context is a no-op
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_can_caller_no_caller_is_noop(t_init, t_wizard):
    # Outside any ContextManager there is no caller — should not raise
    obj = Object.objects.create(name="noop obj", owner=t_wizard)
    obj.can_caller("read", obj)  # must not raise


# ---------------------------------------------------------------------------
# allow / deny create Access rows
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_allow_group_creates_access_row(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("allow obj")
        obj.allow("everyone", "read")
    assert Access.objects.filter(object=obj, rule="allow", group="everyone").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deny_group_creates_access_row(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("deny obj")
        obj.deny("everyone", "write")
    assert Access.objects.filter(object=obj, rule="deny", group="everyone").exists()


# ---------------------------------------------------------------------------
# deny() evicts cached True results
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deny_evicts_cached_true(t_init, t_wizard):
    player = Object.objects.create(name="player")
    with _ctx(t_wizard):
        obj = create("evict obj")
        obj.allow(player, "read")
    with _ctx(t_wizard):
        # populate cache with True
        assert player.is_allowed("read", obj)
        # add deny — must evict cached result
        obj.deny(player, "read")
        assert not player.is_allowed("read", obj)


# ---------------------------------------------------------------------------
# is_allowed — group checks
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_allowed_group_everyone(t_init, t_wizard):
    stranger = Object.objects.create(name="stranger")
    with _ctx(t_wizard):
        obj = create("public obj")
        obj.allow("everyone", "read")
    assert stranger.is_allowed("read", obj)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_allowed_group_owners(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("owner obj")
        obj.allow("owners", "write")
    player = Object.objects.create(name="player")
    # wizard owns it, player does not
    assert t_wizard.is_allowed("write", obj)
    assert not player.is_allowed("write", obj)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_allowed_group_wizards(t_init, t_wizard):
    Player.objects.filter(avatar=t_wizard).update(wizard=True)
    with _ctx(t_wizard):
        obj = create("wiz obj")
        obj.allow("wizards", "develop")
    player = Object.objects.create(name="player")
    assert t_wizard.is_allowed("develop", obj)
    assert not player.is_allowed("develop", obj)


# ---------------------------------------------------------------------------
# is_allowed — specific accessor
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_allowed_specific_accessor(t_init, t_wizard):
    player = Object.objects.create(name="player")
    with _ctx(t_wizard):
        obj = create("accessor obj")
        obj.allow(player, "write")
    assert player.is_allowed("write", obj)
    stranger = Object.objects.create(name="stranger2")
    assert not stranger.is_allowed("write", obj)


# ---------------------------------------------------------------------------
# deny beats allow
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deny_overrides_allow(t_init, t_wizard):
    player = Object.objects.create(name="player")
    with _ctx(t_wizard):
        obj = create("mixed obj")
        obj.allow("everyone", "anything")
        obj.deny(player, "write")
    assert player.is_allowed("read", obj)
    assert not player.is_allowed("write", obj)


# ---------------------------------------------------------------------------
# fatal=True raises PermissionError
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_allowed_fatal_raises(t_init, t_wizard):
    stranger = Object.objects.create(name="stranger fatal")
    with _ctx(t_wizard):
        obj = create("fatal obj")
    with pytest.raises(PermissionError):
        stranger.is_allowed("write", obj, fatal=True)


# ---------------------------------------------------------------------------
# _get_permission_id caching
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_get_permission_id_returns_pk(t_init, t_wizard):
    perm = Permission.objects.get(name="read")
    with _ctx(t_wizard):
        pk = _get_permission_id("read")
    assert pk == perm.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_regular_user_can_read_a_thing(t_init: Object, t_wizard: Object):
    thing = Object.objects.create(name="thing", owner=t_wizard)
    user = Object.objects.create(name="player")
    assert user.is_allowed("read", thing)
    assert not user.is_allowed("write", thing)
    assert not user.is_allowed("entrust", thing)
    assert not user.is_allowed("move", thing)
    assert not user.is_allowed("transmute", thing)
    assert not user.is_allowed("derive", thing)
    assert not user.is_allowed("develop", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_regular_user_who_owns_a_thing(t_init: Object, t_wizard: Object):
    user = Object.objects.create(name="player")
    thing = Object.objects.create(name="thing", owner=user)
    assert user.is_allowed("read", thing)
    assert user.is_allowed("write", thing)
    assert user.is_allowed("entrust", thing)
    assert user.is_allowed("move", thing)
    assert user.is_allowed("transmute", thing)
    assert user.is_allowed("derive", thing)
    assert user.is_allowed("develop", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_everyone_can_read_a_thing(t_init: Object, t_wizard: Object):
    thing = Object.objects.create(name="thing")
    jim = Object.objects.create(name="Jim", unique_name=True)
    assert jim.is_allowed("read", thing)
    assert not jim.is_allowed("write", thing)
    assert not jim.is_allowed("entrust", thing)
    assert not jim.is_allowed("move", thing)
    assert not jim.is_allowed("transmute", thing)
    assert not jim.is_allowed("derive", thing)
    assert not jim.is_allowed("develop", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_wizard_can_do_most_things(t_init: Object, t_wizard: Object):
    # Objects are only Wizards if they have an associated Player with wizard=True
    Player.objects.create(avatar=t_wizard, wizard=True)
    thing = Object.objects.create(name="thing")
    assert t_wizard.is_allowed("read", thing)
    assert t_wizard.is_allowed("write", thing)
    assert t_wizard.is_allowed("entrust", thing)
    assert t_wizard.is_allowed("move", thing)
    assert t_wizard.is_allowed("transmute", thing)
    assert t_wizard.is_allowed("derive", thing)
    assert t_wizard.is_allowed("develop", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_add_a_simple_deny_clase(t_init: Object, t_wizard: Object):
    user = Object.objects.create(name="player")
    thing = Object.objects.create(name="thing", owner=user)
    thing.allow("everyone", "anything")
    thing.deny(user, "write")

    assert user.is_allowed("read", thing)
    assert not user.is_allowed("write", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_create_child_of_an_object_that_isnt_yours(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.create(name="Player")
    parent_thing = Object.objects.create(name="parent thing", owner=t_wizard)
    with code.ContextManager(user, _writer):
        child_thing = Object.objects.create(name="child thing", owner=user)
        with pytest.raises(PermissionError) as excinfo:
            child_thing.parents.add(parent_thing)
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed to 'derive' on #{parent_thing.pk} (parent thing)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_create_parent_of_an_object_that_isnt_yours(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.create(name="Player")
    child_thing = Object.objects.create(name="child thing", owner=t_wizard)
    with code.ContextManager(user, _writer):
        parent_thing = Object.objects.create(name="parent thing", owner=user)
        with pytest.raises(PermissionError) as excinfo:
            child_thing.parents.add(parent_thing)
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed to 'transmute' on #{child_thing.pk} (child thing)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_change_owner_unless_allowed_to_entrust(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.create(name="Player")
    with code.ContextManager(user, _writer):
        with pytest.raises(PermissionError) as excinfo:
            create("thing", owner=t_wizard)
        assert str(excinfo.value) == "Can't change owner at creation time."
        obj = create("thing")
        with pytest.raises(PermissionError) as excinfo:
            obj.owner = t_wizard
            obj.save()
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed to 'entrust' on #{obj.pk} (thing)"
    with code.ContextManager(t_wizard, _writer):
        obj = lookup("thing")
        obj.allow(user, "entrust")
        obj.allow(user, "write")
    with code.ContextManager(user, _writer):
        obj = lookup("thing")
        obj.owner = t_wizard
        obj.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_change_location_unless_allowed_to_move(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        obj = create("thing")
    user = Object.objects.create(name="Player")
    with code.ContextManager(user, _writer):
        obj = lookup("thing")
        obj.location = user
        with pytest.raises(PermissionError) as excinfo:
            obj.save()
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed to 'write' on #{obj.pk} (thing)"
    with code.ContextManager(t_wizard, _writer):
        obj = lookup("thing")
        obj.allow(user, "move")
        obj.allow(user, "write")
    with code.ContextManager(user, _writer):
        obj = lookup("thing")
        obj.location = user
        obj.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_enterfunc(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        containers = lookup("container class")
        box = create("box", parents=[containers])
        box.add_verb("enterfunc", code="print(args[0])")
        thing = create("thing")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            thing.location = box
            thing.save()
    assert any(f"#{thing.pk} (thing)" in str(warning.message) for warning in w.list)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_exitfunc(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    with code.ContextManager(t_wizard, _writer):
        containers = lookup("container class")
        box = create("box", parents=[containers])
        box.add_verb("exitfunc", code="print(args[0])")
        thing = create("thing", location=box)
        assert thing.location == box
    with code.ContextManager(t_wizard, _writer):
        thing = lookup("thing")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as w:
            thing.location = t_wizard.location
            thing.save()
        assert thing.location == t_wizard.location
    assert any(f"#{thing.pk} (thing)" in str(warning.message) for warning in w.list)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_accept(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.create(name="player")
    with code.ContextManager(user, _writer):
        box = create("box")
        box.add_verb("accept", code="return False")
        with pytest.raises(PermissionError) as excinfo:
            thing = create("thing", location=box)
        thing = lookup("thing")
        assert str(excinfo.value) == f"#{box.pk} (box) did not accept #{thing.pk} (thing)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_perm_cache_avoids_repeated_queries(t_init: Object, t_wizard: Object):
    thing = Object.objects.create(name="thing", owner=t_wizard)
    with code.ContextManager(t_wizard, lambda m: None):
        # First call populates the cache.
        assert t_wizard.is_allowed("read", thing)
        queries_after_first = len(connection.queries)
        # Second call for the same (caller, permission, subject) should hit the cache.
        assert t_wizard.is_allowed("read", thing)
        assert len(connection.queries) == queries_after_first


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_perm_cache_invalidated_by_deny(t_init: Object, t_wizard: Object):
    user = Object.objects.create(name="player")
    thing = Object.objects.create(name="thing", owner=user)
    with code.ContextManager(t_wizard, lambda m: None):
        # Populate cache with True for "read".
        assert user.is_allowed("read", thing)
        # Add a deny rule — cache should be evicted.
        thing.deny(user, "read")
        # Now the result must reflect the deny rule, not the stale cache.
        assert not user.is_allowed("read", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_checks_recursion(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        containers = lookup("container class")
        box = create("box", parents=[containers])
        envelope = create("envelope", parents=[containers], location=box)
        with pytest.raises(exceptions.RecursiveError) as excinfo:
            box.location = envelope
            box.save()
        assert str(excinfo.value) == f"#{box.pk} (box) already contains #{envelope.pk} (envelope)"
