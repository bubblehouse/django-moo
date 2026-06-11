# -*- coding: utf-8 -*-
"""
Security tests: queryset-level wizard guards.

Player, UniversalWizard, and the Preposition family have wizard-only
save()/delete() overrides, but Django's QuerySet.update()/delete() and
bulk_create()/bulk_update() never call those methods. WizardGuardedManager
closes that bypass; these tests pin the guard down.
"""

import pytest
from django.contrib.auth import get_user_model

from moo.core.exceptions import AccessError
from moo.core.models.auth import Player, UniversalWizard
from moo.core.models.object import Object
from moo.core.models.verb import Preposition, PrepositionName, PrepositionSpecifier

from .utils import ctx


def make_plain(t_wizard, name):
    """Create a non-wizard Object to act as the restricted caller."""
    from moo.sdk import create

    with ctx(t_wizard):
        return create(name)


def make_player_row():
    """Create a sacrificial Player row outside any caller context."""
    user = get_user_model().objects.create_user(username="qs-guard-user", password="OldPassword1!")
    return Player.objects.create(user=user, wizard=False)


# ---------------------------------------------------------------------------
# Player queryset mutations
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_queryset_update_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_update_plain")
    row = make_player_row()

    with ctx(plain):
        with pytest.raises(AccessError):
            Player.objects.filter(pk=row.pk).update(wizard=True)

    row.refresh_from_db()
    assert row.wizard is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_queryset_delete_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_delete_plain")
    row = make_player_row()

    with ctx(plain):
        with pytest.raises(AccessError):
            Player.objects.filter(pk=row.pk).delete()

    assert Player.objects.filter(pk=row.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_queryset_update_allowed_for_wizard(t_init: Object, t_wizard: Object):
    row = make_player_row()

    with ctx(t_wizard):
        Player.objects.filter(pk=row.pk).update(wizard=True)

    row.refresh_from_db()
    assert row.wizard is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_queryset_delete_allowed_for_wizard(t_init: Object, t_wizard: Object):
    row = make_player_row()

    with ctx(t_wizard):
        Player.objects.filter(pk=row.pk).delete()

    assert not Player.objects.filter(pk=row.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_bulk_create_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_bulk_create_plain")
    before = Player.objects.count()

    with ctx(plain):
        with pytest.raises(AccessError):
            Player.objects.bulk_create([Player(wizard=True)])

    assert Player.objects.count() == before


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_bulk_update_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_bulk_update_plain")
    row = make_player_row()
    row.wizard = True

    with ctx(plain):
        with pytest.raises(AccessError):
            Player.objects.bulk_update([row], ["wizard"])

    row.refresh_from_db()
    assert row.wizard is False


# ---------------------------------------------------------------------------
# UniversalWizard queryset mutations
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_universal_wizard_queryset_mutation_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_uw_plain")
    user = get_user_model().objects.create_user(username="qs-uw-user", password="OldPassword1!")
    row = UniversalWizard.objects.create(user=user)

    with ctx(plain):
        with pytest.raises(AccessError):
            UniversalWizard.objects.filter(pk=row.pk).delete()

    assert UniversalWizard.objects.filter(pk=row.pk).exists()


# ---------------------------------------------------------------------------
# Preposition family queryset mutations
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_preposition_queryset_mutations_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    plain = make_plain(t_wizard, "qs_prep_plain")
    counts = (
        Preposition.objects.count(),
        PrepositionName.objects.count(),
        PrepositionSpecifier.objects.count(),
    )

    with ctx(plain):
        with pytest.raises(AccessError):
            Preposition.objects.all().delete()
        with pytest.raises(AccessError):
            PrepositionName.objects.all().update(name="hijacked")
        with pytest.raises(AccessError):
            PrepositionName.objects.all().delete()
        with pytest.raises(AccessError):
            PrepositionSpecifier.objects.all().update(specifier="none")
        with pytest.raises(AccessError):
            PrepositionSpecifier.objects.all().delete()

    assert counts == (
        Preposition.objects.count(),
        PrepositionName.objects.count(),
        PrepositionSpecifier.objects.count(),
    )
    assert not PrepositionName.objects.filter(name="hijacked").exists()


# ---------------------------------------------------------------------------
# Guard boundaries
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_queryset_guard_inert_outside_context(t_init: Object, t_wizard: Object):
    """Management commands and system code run with no caller; the guard must not fire."""
    row = make_player_row()

    Player.objects.filter(pk=row.pk).update(wizard=True)

    row.refresh_from_db()
    assert row.wizard is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_remove_player_record_still_works_for_wizard(t_init: Object, t_wizard: Object):
    """Regression: the one production queryset delete on Player still works."""
    from moo.sdk import create
    from moo.sdk.objects import remove_player_record

    with ctx(t_wizard):
        avatar = create("qs_npc_avatar")
    Player.objects.create(avatar=avatar)

    with ctx(t_wizard):
        deleted = remove_player_record(avatar)

    assert deleted == 1
    assert not Player.objects.filter(avatar=avatar).exists()
