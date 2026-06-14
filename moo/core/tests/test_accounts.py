"""Tests for the account model (spec 200, item G).

The :class:`Player` row is the durable account anchor; these cover resolving an
avatar to its account and back, the stable account id, and the moderation
status helpers the safety set (H/I/J) reads from.
"""

import datetime

import pytest
from django.utils import timezone

from .. import code, create
from ..models import Object, Player
from ...sdk import account_for, avatars_of, account_id_for, current_account


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_account_for_resolves_avatar(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
    assert isinstance(account, Player)
    assert account.avatar == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_account_for_non_avatar_and_none(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        widget = create("widget")
        assert account_for(widget) is None
        assert account_for(None) is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_account_id_is_stable_across_rename(t_init: Object, t_wizard: Object):
    """The account id is the Player pk — it does not move when the avatar renames."""
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        before = account.account_id
        t_wizard.name = "Renamed Wizard"
        t_wizard.save()
        account.refresh_from_db()
    assert account.account_id == before
    assert account.pk == before


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_account_id_for_is_cheap_lookup(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        assert account_id_for(t_wizard) == account.pk
        assert account_id_for(None) is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_avatars_of_returns_list(t_init: Object, t_wizard: Object):
    """avatars_of returns a list so the later multi-avatar model needs no caller change."""
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        assert avatars_of(account) == [t_wizard]
        assert avatars_of(None) == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_current_account_from_context(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        assert current_account() == account_for(t_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_status_defaults_to_active(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
    assert account.status == Player.STATUS_ACTIVE
    assert account.is_suspended() is False
    assert account.login_blocked_reason() is None
    assert account.is_registered() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_suspension_in_force_and_expired(t_init: Object, t_wizard: Object):
    now = timezone.now()
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        account.status = Player.STATUS_SUSPENDED
        account.suspended_until = now + datetime.timedelta(hours=1)
        account.save()
    # In force while the deadline is in the future.
    assert account.is_suspended(now) is True
    assert account.login_blocked_reason(now) is not None
    # Treated as expired once the deadline passes.
    later = now + datetime.timedelta(hours=2)
    assert account.is_suspended(later) is False
    assert account.login_blocked_reason(later) is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_open_ended_suspension_stays_in_force(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        account.status = Player.STATUS_SUSPENDED
        account.suspended_until = None
        account.save()
    assert account.is_suspended() is True
    assert account.login_blocked_reason() == "This account is suspended."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ban_blocks_login(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        account.status = Player.STATUS_BANNED
        account.save()
    assert account.login_blocked_reason() == "This account has been banned."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_registered_identity(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account = account_for(t_wizard)
        account.registered_identity = "phil@example.org"
        account.save()
    assert account.is_registered() is True
