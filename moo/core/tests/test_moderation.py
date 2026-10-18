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
    unban,
    mute,
    unmute,
    is_muted,
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
def test_unban_reinstates_and_clears_the_blacklist(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        account.registered_identity = "reformed@example.org"
        account.save()
        ban(account, reason="spam")
        unban(account, reason="appeal granted")
        account.refresh_from_db()
        assert account.status == Player.STATUS_ACTIVE
        assert not Blacklist.objects.filter(identity="reformed@example.org").exists()
        assert account_login_blocked(account) is None
        assert AuditLog.objects.filter(action="unban", detail="appeal granted").exists()


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
        for lift in (unsuspend, unban, unmute):
            with pytest.raises(UserError, match="Staff"):
                lift(wizard_account)


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
def test_suspend_zero_hours_is_immediate_not_open_ended(t_init: Object, t_wizard: Object):
    # ``hours=0`` must mean an already-expired suspension, not a permanent one.
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        suspend(account, hours=0)
        account.refresh_from_db()
        assert account.suspended_until is not None
        assert account.is_suspended() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_expired_suspension_cleared_at_login(t_init: Object, t_wizard: Object):
    import datetime

    from django.utils import timezone

    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(lookup("Player"))
        account.status = Player.STATUS_SUSPENDED
        account.suspended_until = timezone.now() - datetime.timedelta(hours=1)
        account.save()
    # The login chokepoint allows the lapsed account and clears the stale flag.
    assert account_login_blocked(account) is None
    account.refresh_from_db()
    assert account.status == Player.STATUS_ACTIVE
    assert account.suspended_until is None


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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_mute_is_staff_only_account_keyed_and_lapses(t_init: Object, t_wizard: Object):
    """Staff mute an account; a player cannot; staff cannot be muted; an expired mute lapses."""
    player = lookup("Player")
    account = account_for(player)
    with code.ContextManager(player, lambda _: None):
        with pytest.raises(AccessError):
            mute(account_for(t_wizard))
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.raises(UserError):
            mute(account_for(t_wizard))
        mute(account, hours=1)
        assert is_muted(account)
        assert AuditLog.objects.filter(action="mute").exists()
        unmute(account)
        account.refresh_from_db()
        assert not is_muted(account)
        mute(account)
        assert is_muted(account)
        unmute(account)
        account.refresh_from_db()
        assert not is_muted(account)
        assert AuditLog.objects.filter(action="unmute").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sanctions_call_the_avatar_hook(t_init: Object, t_wizard: Object):
    """suspend, ban, and mute call on_sanction on the avatar, as the avatar; a failing hook keeps the sanction."""
    player = lookup("Player")
    account = account_for(player)

    def last_sanction():
        # The hook runs as its own task; read in a fresh session so no cached value hides its write.
        with code.ContextManager(t_wizard, lambda _: None):
            return lookup("Player").get_property("last_sanction")

    with code.ContextManager(t_wizard, lambda _: None):
        player.add_verb(
            "on_sanction",
            code="from moo.sdk import context\nthis.set_property('last_sanction', [args[0], context.player.name])\n",
            replace=True,
        )
        mute(account, hours=1)
    assert last_sanction() == ["mute", "Player"]
    with code.ContextManager(t_wizard, lambda _: None):
        suspend(account, hours=1)
    assert last_sanction() == ["suspend", "Player"]
    with code.ContextManager(t_wizard, lambda _: None):
        player.add_verb("on_sanction", code="raise ValueError('broken hook')\n", replace=True)
        try:
            ban(account)
        except ValueError:
            pass  # An eager test task can surface the hook's error; the ban still stands.
    account.refresh_from_db()
    assert account.status == Player.STATUS_BANNED


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_mute_needs_positive_hours_and_expires(t_init: Object, t_wizard: Object):
    """Zero or negative hours are refused; a mute whose deadline passed reads as lapsed."""
    import datetime  # pylint: disable=import-outside-toplevel

    from django.utils import timezone  # pylint: disable=import-outside-toplevel

    account = account_for(lookup("Player"))
    with code.ContextManager(t_wizard, lambda _: None):
        for hours in (0, -1):
            with pytest.raises(UserError):
                mute(account, hours=hours)
        mute(account, hours=1)
    account.muted_until = timezone.now() - datetime.timedelta(seconds=1)
    assert not is_muted(account)
