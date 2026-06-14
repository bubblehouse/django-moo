"""Tests for the suspend/ban sanction primitives (spec 200, item H)."""

import pytest

from .. import code
from ..exceptions import UserError, AccessError
from ..models import Object, Player, AuditLog, Blacklist
from ...sdk import (
    lookup,
    account_for,
    suspend,
    unsuspend,
    ban,
    is_blacklisted,
    account_login_blocked,
)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suspend_blocks_login_then_unsuspend_clears(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        suspend(account, hours=24)
        account.refresh_from_db()
        assert account.status == Player.STATUS_SUSPENDED
        assert account.suspended_until is not None
        assert account_login_blocked(account) is not None
        assert AuditLog.objects.filter(action="suspend").exists()

        unsuspend(account)
        account.refresh_from_db()
        assert account.status == Player.STATUS_ACTIVE
        assert account.suspended_until is None
        assert account_login_blocked(account) is None
        assert AuditLog.objects.filter(action="unsuspend").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_ban_blacklists_identity(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        account.registered_identity = "griefer@example.org"
        account.save()
        ban(account)
        account.refresh_from_db()
        assert account.status == Player.STATUS_BANNED
        assert Blacklist.objects.filter(identity="griefer@example.org").exists()
        assert is_blacklisted("griefer@example.org") is True
        assert account_login_blocked(account) is not None
        assert AuditLog.objects.filter(action="ban").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_cannot_sanction_staff(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        wizard_account = account_for(t_wizard)
        assert wizard_account.wizard is True
        with pytest.raises(UserError, match="Staff"):
            suspend(wizard_account, hours=1)
        with pytest.raises(UserError, match="Staff"):
            ban(wizard_account)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_non_staff_caller_refused(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        player = lookup("Player")
        target = account_for(player)
    # Caller is the non-wizard player.
    with code.ContextManager(player, lambda _: None):
        with pytest.raises(AccessError):
            suspend(target, hours=1)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_login_blocked_composes_status_and_blacklist(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        # An account that is itself fine but whose identity was blacklisted
        # elsewhere is still blocked.
        account.registered_identity = "shared@example.org"
        account.status = Player.STATUS_ACTIVE
        account.save()
        Blacklist.objects.create(identity="shared@example.org", site=account.site)
        assert account_login_blocked(account) == "This identity has been banned."
