"""Tests for non-destructive recovery: soft-delete / restore (spec 200, item K)."""

import datetime

import pytest
from django.utils import timezone

from .. import code, create
from ..models import Object
from ...sdk import (
    lookup,
    soft_recycle,
    restore,
    destroy,
    get_recycled,
    sweep_recycled,
)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_soft_recycle_hides_but_keeps_identity(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        room = create("Room", parents=[lookup("Generic Room")])
        widget = create("widget", location=room)
        pk = widget.pk
        soft_recycle(widget)
        # Hidden from the site-scoped default manager (rooms/lookups/parser)...
        assert not Object.objects.filter(pk=pk).exists()
        # ...but the row, its id, and relationships are intact.
        ghost = Object.global_objects.get(pk=pk)
        assert ghost.recycled is True
        assert ghost.recycled_at is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_restore_brings_object_back(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        widget = create("widget", owner=t_wizard)
        pk = widget.pk
        soft_recycle(widget)
        assert not Object.objects.filter(pk=pk).exists()
        ghost = Object.global_objects.get(pk=pk)
        restore(ghost)
        # Visible again with the same id.
        assert Object.objects.filter(pk=pk).exists()
        assert Object.objects.get(pk=pk).recycled is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_soft_recycle_refunds_quota_once(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.set_property("ownership_quota", 5)
        widget = create("widget")  # quota 5 -> 4
        assert t_wizard.get_property("ownership_quota") == 4
        soft_recycle(widget)  # refund -> 5
        assert t_wizard.get_property("ownership_quota") == 5
        # Hard-destroying the already-recycled object must not refund again.
        ghost = Object.global_objects.get(pk=widget.pk)
        destroy(ghost)
        assert t_wizard.get_property("ownership_quota") == 5


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_destroy_is_permanent(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        widget = create("widget")
        pk = widget.pk
        destroy(widget)
        assert not Object.global_objects.filter(pk=pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_recycled_lists_for_owner(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        a = create("alpha")
        create("beta")  # left alone
        soft_recycle(a)
        recycled = get_recycled(owner=t_wizard)
        assert [o.pk for o in recycled] == [a.pk]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sweep_purges_old_recycled(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        widget = create("widget")
        pk = widget.pk
        soft_recycle(widget)
        # Backdate the recycle so the sweep considers it expired.
        Object.global_objects.filter(pk=pk).update(recycled_at=timezone.now() - datetime.timedelta(days=60))
        purged = sweep_recycled(older_than_days=30)
        assert purged >= 1
        assert not Object.global_objects.filter(pk=pk).exists()
