"""Tests for always-on provenance and tagged output (spec 200, item E)."""

import pytest

from .. import code
from .. import _build_envelope, current_provenance
from ..exceptions import UserError
from ..models import Object
from ...sdk import (
    lookup,
    notify,
    capture_provenance_stack,
    resolve_provenance_account,
    account_for,
)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_envelope_carries_provenance_and_kind(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        player = lookup("Player")
        code.ContextManager.override_caller(caller=t_wizard, this=player, verb_name="poke")
        env = _build_envelope("hello", kind="say")
        prov = current_provenance()
    assert env["message"] == "hello"
    assert env["kind"] == "say"
    assert env["caller_id"] == t_wizard.pk
    assert env["provenance"]["verb"] == "poke"
    assert env["provenance"]["origin"] == player.pk
    assert env["provenance"]["owner"] == t_wizard.pk
    # The hot-path single-frame triple matches what the envelope embeds.
    assert prov == env["provenance"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_default_kind_is_text(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        env = _build_envelope("plain")
    assert env["kind"] == "text"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_provenance_none_without_frame(t_init: Object, t_wizard: Object):
    # Active task but no verb frame pushed yet -> no provenance to record.
    with code.ContextManager(t_wizard, lambda _: None):
        assert current_provenance() is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_capture_provenance_stack(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        player = lookup("Player")
        code.ContextManager.override_caller(caller=t_wizard, this=player, verb_name="a")
        frames = capture_provenance_stack()
    assert frames[-1]["verb"] == "a"
    assert frames[-1]["owner"] == t_wizard.pk
    assert frames[-1]["origin"] == player.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_resolve_provenance_account(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        code.ContextManager.override_caller(caller=t_wizard, this=t_wizard, verb_name="x")
        prov = current_provenance()
        acct_id = resolve_provenance_account(prov)
        assert acct_id == account_for(t_wizard).pk
        assert resolve_provenance_account(None) is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_notify_rejects_unknown_kind(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.raises(UserError, match="Unknown output kind"):
            notify(t_wizard, "x", kind="bogus")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_notify_system_requires_wizard_initiator(t_init: Object, t_wizard: Object):
    """A wizard-owned verb run on behalf of an ordinary user cannot forge a system line."""
    with code.ContextManager(t_wizard, lambda _: None):
        player = lookup("Player")  # non-wizard avatar
    with code.ContextManager(t_wizard, lambda _: None, player=player):
        with pytest.raises(UserError, match="wizard"):
            notify(player, "FAKE SYSTEM NOTICE", kind="system")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_notify_system_allowed_for_wizard_initiator(t_init: Object, t_wizard: Object):
    # Wizard initiator (player defaults to the wizard caller) may emit system.
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.warns(RuntimeWarning):
            notify(t_wizard, "real system notice", kind="system")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_notify_say_allowed(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.warns(RuntimeWarning):
            notify(t_wizard, "hello there", kind="say")
