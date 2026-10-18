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

        printed.clear()
        parse.interpret(ctx, "@unban Player")
        account.refresh_from_db()
        assert account.status == Player.STATUS_ACTIVE
        assert any("Unbanned" in p for p in printed)


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sanctions_record_a_reason(t_init: Object, t_wizard: Object):
    """`because <reason>` lands in each sanction's audit entry, and `for <hours>` still reads."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        account = account_for(player)
        parse.interpret(ctx, "@mute Player for 2 because rule 4: spam")
        parse.interpret(ctx, "@unmute Player because appeal granted")
        parse.interpret(ctx, "@suspend Player for 12 because rule 2")
        parse.interpret(ctx, "@unsuspend Player because served")
        parse.interpret(ctx, "@ban Player because rule [9]")
        parse.interpret(ctx, "@unban Player because mistaken identity")
        account.refresh_from_db()
        assert account.status == Player.STATUS_ACTIVE
        assert any("for 2.0 hour(s)" in p for p in printed), printed
    details = dict(AuditLog.objects.values_list("action", "detail"))
    assert details["mute"] == "rule 4: spam"
    assert details["unmute"] == "appeal granted"
    assert details["suspend"] == "rule 2"
    assert details["unsuspend"] == "served"
    assert details["ban"] == "rule (9)"
    assert details["unban"] == "mistaken identity"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sanction_names_a_miss(t_init: Object, t_wizard: Object):
    """A sanction naming nobody says so and records nothing."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@ban Nobodyatall because spam")
    assert any("no one named 'Nobodyatall'" in p for p in printed), printed
    assert not AuditLog.objects.filter(action="ban").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_auditlog_shows_the_detail(t_init: Object, t_wizard: Object):
    """@auditlog prints each entry's detail under it, so staff see the reason."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@suspend Player for 1 because rule 2: spam")
        printed.clear()
        parse.interpret(ctx, "@auditlog")
    assert any(str(p).strip() == "rule 2: spam" for p in printed), printed
