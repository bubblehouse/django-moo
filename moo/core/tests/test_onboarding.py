"""Tests for the guest tier (I) and registration gate (J) — spec 200."""

import pytest

from .. import code, create
from ..exceptions import QuotaError, UserError
from ..models import Object, Player, Blacklist
from ...sdk import (
    provision_guest,
    remove_guest,
    is_guest,
    register,
    require_registered,
)


def reject_all_verifier(identity):
    """A stricter pluggable verifier used to prove the hook is honored."""
    return False, None, "Registration is closed."


# --- I: guest tier --------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_provision_guest_creates_guest_account(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, avatar = provision_guest("Visitor")
        assert is_guest(account) is True
        assert account.status == Player.STATUS_GUEST
        assert avatar.is_player() is True
        assert any(p.name == "Generic Guest" for p in avatar.parents.all())


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_guest_cannot_create(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        _, avatar = provision_guest("Visitor")
    # As the guest, creation is refused by quota (own quota of 0).
    with code.ContextManager(avatar, lambda _: None):
        with pytest.raises(QuotaError):
            create("contraband")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_remove_guest_is_non_persistent(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, avatar = provision_guest("Visitor")
        avatar_pk = avatar.pk
        assert remove_guest(account) is True
        assert not Object.objects.filter(pk=avatar_pk).exists()
        # A non-guest is left alone.
        assert remove_guest(None) is False


# --- J: registration gate -------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_register_binds_identity_and_promotes_guest(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, _ = provision_guest("Visitor")
        register(account, "Newcomer@Example.ORG")
        account.refresh_from_db()
        assert account.registered_identity == "newcomer@example.org"  # normalized
        assert account.status == Player.STATUS_ACTIVE
        assert account.is_registered() is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_register_rejects_empty_identity(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, _ = provision_guest("Visitor")
        with pytest.raises(UserError):
            register(account, "   ")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_register_refuses_blacklisted_identity(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, _ = provision_guest("Visitor")
        Blacklist.objects.create(identity="banned@example.org")
        with pytest.raises(UserError, match="banned"):
            register(account, "banned@example.org")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_require_registered_gate(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        account, _ = provision_guest("Visitor")
        with pytest.raises(UserError, match="register"):
            require_registered(account)
        register(account, "ok@example.org")
        assert require_registered(account) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_pluggable_verifier_is_honored(settings, t_init: Object, t_wizard: Object):
    settings.MOO_REGISTRATION_VERIFIER = "moo.core.tests.test_onboarding.reject_all_verifier"
    with code.ContextManager(t_wizard, lambda _: None):
        account, _ = provision_guest("Visitor")
        with pytest.raises(UserError, match="closed"):
            register(account, "anything@example.org")
