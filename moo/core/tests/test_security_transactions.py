"""
Engine state that outlives a rolled-back command.

A command runs in one transaction, and a command that raises rolls it back. The
Redis attribute cache, queued Celery tasks, and site-unscoped queries all sit
outside that transaction, so each could carry a rolled-back write, or another
universe's rows, into the next command.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.db import transaction

from .. import code
from ..models import ExternalKey, Object
from ...sdk import create, get_or_create_by_key, invoke, lookup


@pytest.fixture
def redis_cache(settings):
    """Turn the cross-session attribute cache on (tests run with it off) and empty it afterwards."""
    settings.MOO_ATTRIB_CACHE_TTL = 120
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.usefixtures("redis_cache")
def test_rolled_back_property_write_never_reaches_the_cache(t_init: Object, t_wizard: Object):
    """
    ``set_property`` evicted the Redis key, and a later ``get_property`` in the same
    transaction refilled it with the new value. When the command then raised, the
    database rolled back but Redis kept the value for the cache TTL, and the next
    locked read-modify-write saved it. The session now bypasses Redis for keys it wrote.
    """
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("Cached Thing", location=None)
        obj.set_property("state", "clean")
    with pytest.raises(RuntimeError):
        with code.ContextManager(t_wizard, lambda _: None):
            with transaction.atomic():
                obj.set_property("state", "dirty")
                assert obj.get_property("state") == "dirty"
                raise RuntimeError("the command failed")
    with code.ContextManager(t_wizard, lambda _: None):
        assert lookup(obj.pk).get_property("state") == "clean"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.usefixtures("redis_cache")
def test_commit_evicts_a_value_cached_before_it(t_init: Object, t_wizard: Object):
    """
    Another session that reads between a write and its commit caches the old value.
    The keys are evicted again on commit, so that stale entry does not survive.
    """
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("Cached Thing", location=None)
        obj.set_property("state", "old")
        with transaction.atomic():
            obj.set_property("state", "new")
            # What a concurrent reader would leave behind: the committed value.
            cache.set(f"moo:prop:{obj.pk}:state:1", '"old"')
        assert cache.get(f"moo:prop:{obj.pk}:state:1") is None
    with code.ContextManager(t_wizard, lambda _: None):
        assert lookup(obj.pk).get_property("state") == "new"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.usefixtures("redis_cache")
def test_cache_still_serves_unwritten_keys(t_init: Object, t_wizard: Object):
    """A key this session did not write is still read from and stored in Redis."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("Cached Thing", location=None)
        obj.set_property("state", "steady")
    with code.ContextManager(t_wizard, lambda _: None):
        assert lookup(obj.pk).get_property("state") == "steady"
    assert cache.get(f"moo:prop:{obj.pk}:state:1") == '"steady"'


def _fake_verb():
    verb = MagicMock()
    verb._invoked_object.pk = 1  # pylint: disable=protected-access
    verb._invoked_name = "test"  # pylint: disable=protected-access
    return verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_invoke_waits_for_the_commit(t_init: Object, t_wizard: Object):
    """
    ``invoke()`` queued its task at once, so the task ran even when the command
    that queued it raised and rolled back. It now queues on commit.
    """
    with patch("moo.core.tasks.invoke_verb.apply_async") as apply_async:
        with pytest.raises(RuntimeError):
            with code.ContextManager(t_wizard, lambda _: None):
                with transaction.atomic():
                    invoke(verb=_fake_verb())
                    raise RuntimeError("the command failed")
        assert not apply_async.called
        with code.ContextManager(t_wizard, lambda _: None):
            with transaction.atomic():
                invoke(verb=_fake_verb())
                assert not apply_async.called
        assert apply_async.call_count == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_external_keys_are_scoped_to_the_active_site(t_two_sites):
    """
    ``ExternalKey.objects`` returned every Site's keys, so a dataset that queried it
    directly while building a second universe found the first universe's objects
    and built nothing. It now filters to the active Site, like ``Object.objects``.
    """
    site1, site2 = t_two_sites
    wizard1 = Object.global_objects.get(name="Wizard", site=site1)
    wizard2 = Object.global_objects.get(name="Wizard", site=site2)
    with code.ContextManager(wizard1, lambda _: None, site=site1):
        get_or_create_by_key("zone", "plaza", name="Plaza")
    with code.ContextManager(wizard2, lambda _: None, site=site2):
        assert not ExternalKey.objects.filter(namespace="zone").exists()
        obj, created = get_or_create_by_key("zone", "plaza", name="Plaza")
        assert created
        assert list(ExternalKey.objects.filter(namespace="zone").values_list("object_id", flat=True)) == [obj.pk]
    assert ExternalKey.global_objects.filter(namespace="zone").count() == 2
