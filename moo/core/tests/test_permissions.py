import logging

import pytest
from django.db import connection
from django.test import override_settings

from moo.core.models import Object, Player

from .. import code, create, exceptions, lookup


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_regular_user_can_read_a_thing(t_init: Object, t_wizard: Object):
    thing = Object.objects.create(name="thing", owner=t_wizard)
    user = Object.objects.get(name__iexact="player")
    assert user.is_allowed("read", thing)
    assert not user.is_allowed("write", thing)
    assert not user.is_allowed("entrust", thing)
    assert not user.is_allowed("move", thing)
    assert not user.is_allowed("transmute", thing)
    assert not user.is_allowed("derive", thing)
    assert not user.is_allowed("develop", thing)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_regular_user_who_owns_a_thing(t_init: Object, t_wizard: Object):
    user = Object.objects.get(name__iexact="player")
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
    user = Object.objects.get(name__iexact="player")
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

    user = Object.objects.get(name__iexact="player")
    parent_thing = Object.objects.create(name="parent thing", owner=t_wizard)
    with code.ContextManager(user, _writer):
        child_thing = Object.objects.create(name="child thing", owner=user)
        with pytest.raises(PermissionError) as excinfo:
            child_thing.parents.add(parent_thing)
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed derive on #{parent_thing.pk} (parent thing)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_create_parent_of_an_object_that_isnt_yours(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.get(name__iexact="player")
    child_thing = Object.objects.create(name="child thing", owner=t_wizard)
    with code.ContextManager(user, _writer):
        parent_thing = Object.objects.create(name="parent thing", owner=user)
        with pytest.raises(PermissionError) as excinfo:
            child_thing.parents.add(parent_thing)
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed transmute on #{child_thing.pk} (child thing)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cant_change_owner_unless_allowed_to_entrust(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.get(name__iexact="player")
    with code.ContextManager(user, _writer):
        with pytest.raises(PermissionError) as excinfo:
            create("thing", owner=t_wizard)
        assert str(excinfo.value) == "Can't change owner at creation time."
        obj = create("thing")
        with pytest.raises(PermissionError) as excinfo:
            obj.owner = t_wizard
            obj.save()
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed entrust on #{obj.pk} (thing)"
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
    user = Object.objects.get(name__iexact="player")
    with code.ContextManager(user, _writer):
        obj = lookup("thing")
        obj.location = user
        with pytest.raises(PermissionError) as excinfo:
            obj.save()
        assert str(excinfo.value) == f"#{user.pk} (Player) is not allowed write on #{obj.pk} (thing)"
    with code.ContextManager(t_wizard, _writer):
        obj = lookup("thing")
        obj.allow(user, "move")
        obj.allow(user, "write")
    with code.ContextManager(user, _writer):
        obj = lookup("thing")
        obj.location = user
        obj.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_enterfunc(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
        with code.ContextManager(t_wizard, _writer):
            containers = lookup("container class")
            box = create("box", parents=[containers])
            box.add_verb("enterfunc", code="print(args[0])")
            thing = create("thing")
            thing.location = box
            thing.save()
    assert f"#{thing.pk} (thing)\n" in caplog.text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_exitfunc(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
        with code.ContextManager(t_wizard, _writer):
            containers = lookup("container class")
            box = create("box", parents=[containers])
            box.add_verb("exitfunc", code="print(args[0])")
            thing = create("thing", location=box)
            assert thing.location == box
        with code.ContextManager(t_wizard, _writer):
            thing = lookup("thing")
            thing.location = t_wizard.location
            thing.save()
            assert thing.location == t_wizard.location
    assert f"#{thing.pk} (thing)\n" in caplog.text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_change_location_calls_accept(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    user = Object.objects.get(name__iexact="player")
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
    user = Object.objects.get(name__iexact="player")
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
