"""Tests for the action audit log (spec 200, item L)."""

import pytest

from .. import code, create
from ..models import Object, AuditLog
from ...sdk import record_action, query_audit, account_for


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_create_is_audited(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("auditable widget")
        rows = AuditLog.objects.filter(action="create", target_id=obj.pk)
        assert rows.count() == 1
        row = rows.first()
        assert row.actor == account_for(t_wizard)
        assert "auditable widget" in row.target_repr


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_destroy_is_audited(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("doomed")
        pk = obj.pk
        obj.delete()
        rows = AuditLog.objects.filter(action="destroy", target_id=pk)
        assert rows.count() == 1
        # The name snapshot survives the object's deletion.
        assert "doomed" in rows.first().target_repr


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_record_skipped_without_actor():
    # No active session -> no human actor -> not consequential, skipped.
    assert record_action("create") is None
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_force_records_without_actor():
    row = record_action("ban", detail="login-blacklist", force=True)
    assert row is not None
    assert row.actor is None
    assert row.action == "ban"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_query_audit_filters(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        create("alpha")
        beta = create("beta")
        creates = query_audit(action="create")
        assert creates and all(r.action == "create" for r in creates)
        only_beta = query_audit(target=beta)
        assert all(r.target_id == beta.pk for r in only_beta)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_bootstrap_creates_are_not_logged(t_init: Object, t_wizard: Object):
    # The thousands of objects seeded by the bootstrap have no human actor and
    # must not appear in the log — only player-initiated creates do.
    assert AuditLog.objects.filter(actor__isnull=True, action="create").count() == 0
