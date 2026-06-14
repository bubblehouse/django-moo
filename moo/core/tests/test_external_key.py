"""Tests for indexed external-key get-or-create (spec 200, item B)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .. import code, create
from ..models import Object, ExternalKey
from ...sdk import lookup, resolve_by_key, get_or_create_by_key


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_or_create_is_idempotent(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        room_class = lookup("Generic Room")
        obj1, created1 = get_or_create_by_key("zone_slug", "downtown", name="Downtown", parents=[room_class])
        assert created1 is True
        obj2, created2 = get_or_create_by_key("zone_slug", "downtown", name="Downtown", parents=[room_class])
        assert created2 is False
        assert obj1.pk == obj2.pk
        # Re-run created no duplicate object or key.
        assert ExternalKey.objects.filter(namespace="zone_slug", key="downtown").count() == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_resolve_is_single_indexed_query(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        get_or_create_by_key("loc", "plaza", name="Plaza")
        with CaptureQueriesContext(connection) as ctx:
            obj = resolve_by_key("loc", "plaza")
        assert obj is not None
        # One SELECT (with the joined object) — no full Property scan.
        assert len(ctx.captured_queries) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_namespaces_do_not_collide(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        a, _ = get_or_create_by_key("zone_slug", "x", name="Zone X")
        b, _ = get_or_create_by_key("location_slug", "x", name="Location X")
        assert a.pk != b.pk
        assert resolve_by_key("zone_slug", "x").pk == a.pk
        assert resolve_by_key("location_slug", "x").pk == b.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_resolve_missing_returns_none(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        assert resolve_by_key("zone_slug", "nope") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_key_removed_with_object(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        obj, _ = get_or_create_by_key("loc", "doomed", name="Doomed")
        obj.delete()
        assert resolve_by_key("loc", "doomed") is None
