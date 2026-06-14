"""Verb-dispatch tests for the staff sanction commands (spec 200, items H/L)."""

import pytest

from moo.core import code, parse
from moo.core.models import Object, Player, AuditLog
from moo.sdk import lookup, account_for


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suspend_and_unsuspend_verbs(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        parse.interpret(ctx, "@suspend Player for 12")
        account = account_for(player)
        assert account.status == Player.STATUS_SUSPENDED
        assert account.suspended_until is not None
        assert any("Suspended" in p for p in printed)

        printed.clear()
        parse.interpret(ctx, "@unsuspend Player")
        account.refresh_from_db()
        assert account.status == Player.STATUS_ACTIVE
        assert any("Reinstated" in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_ban_verb(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        account = account_for(player)
        account.registered_identity = "x@example.org"
        account.save()
        parse.interpret(ctx, "@ban Player")
        account.refresh_from_db()
        assert account.status == Player.STATUS_BANNED
        assert any("Banned" in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_auditlog_verb_lists_actions(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@suspend Player")
        AuditLog.objects.filter(action="suspend").exists()
        printed.clear()
        parse.interpret(ctx, "@auditlog")
    assert any("suspend" in p for p in printed)
