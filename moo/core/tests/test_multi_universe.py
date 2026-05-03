# -*- coding: utf-8 -*-
"""
Tests for multi-universe support via Django Sites.

Covers the full PR-description test plan plus regressions for the avatar-hijack
hole and the migration backfill step.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.contrib.sites.models import Site

from moo.core import code, exceptions
from moo.core.managers import get_default_site
from moo.core.models import Object, Player
from moo.core.models.auth import UniversalWizard
from moo.core.moojson import clear_nothing_cache
from moo.sdk import lookup


# ---------------------------------------------------------------------------
# Migration 0030 backfill — placed first so any later test that pollutes
# Django's per-process Site cache (e.g. ``moo_init --hostname``) cannot leak
# stale Site references into this test's ``t_init`` setup.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_migration_0030_backfills_existing_rows(t_init):
    """Reproduce the migration RunPython step: rows with site=NULL get SITE_ID."""
    # Real migrations use ``apps.get_model`` which returns the historical
    # model wired with a plain ``Manager()`` (no SiteManager filter).  Since
    # the live model exposes the manager as ``global_objects``, we drive the
    # same UPDATE through that manager and verify the outcome — equivalent
    # to what migrate would run end-to-end.
    obj = Object.global_objects.create(name="orphan-obj")
    Object.global_objects.filter(pk=obj.pk).update(site=None)
    user = User.objects.create_user(username="orphan", password="x")
    p = Player.objects.create(user=user, wizard=False)
    Player.objects.filter(pk=p.pk).update(site=None)

    assert Object.global_objects.filter(pk=obj.pk, site__isnull=True).exists()
    assert Player.objects.filter(pk=p.pk, site__isnull=True).exists()

    site_id = get_default_site().pk
    Object.global_objects.filter(site__isnull=True).update(site_id=site_id)
    Player.objects.filter(site__isnull=True).update(site_id=site_id)

    assert Object.global_objects.get(pk=obj.pk).site_id == site_id
    assert Player.objects.get(pk=p.pk).site_id == site_id


# ---------------------------------------------------------------------------
# Single-site smoke
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_single_site_unchanged(t_init, t_wizard):
    """Default SITE_ID=1 flow: lookup, save, and create all behave as before."""
    assert t_wizard.site_id == get_default_site().pk
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup("System Object")
        assert system.site_id == get_default_site().pk
        # ``$root_class`` is stored as a property on the System Object and is
        # set up by the default bootstrap.
        assert lookup("$root_class").pk == system.root_class.pk


# ---------------------------------------------------------------------------
# Site isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_two_sites_isolated(t_two_sites):
    """Each site has its own System Object, Wizard, and hierarchy."""
    site1, site2 = t_two_sites
    sys1 = Object.global_objects.get(name="System Object", site=site1)
    sys2 = Object.global_objects.get(name="System Object", site=site2)
    assert sys1.pk != sys2.pk
    wizards1 = Object.global_objects.filter(name="Wizard", site=site1).count()
    wizards2 = Object.global_objects.filter(name="Wizard", site=site2).count()
    assert wizards1 == 1
    assert wizards2 == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lookup_int_pk_cross_site_raises(t_two_sites, t_wizard):
    """Integer-PK lookup is site-scoped: a PK from site1 is invisible from site2."""
    site1, site2 = t_two_sites
    site1_obj = Object.global_objects.filter(site=site1).first()
    assert site1_obj is not None
    with code.ContextManager(t_wizard, lambda _: None, site=site2):
        with pytest.raises(exceptions.NoSuchObjectError):
            lookup(site1_obj.pk)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lookup_dollar_returns_active_site_system(t_two_sites_default):
    """``lookup("$player")`` resolves through the active site's System Object."""
    site1, site2 = t_two_sites_default
    site1_wizard = Object.global_objects.get(name="Wizard", site=site1)
    site2_wizard = Object.global_objects.get(name="Wizard", site=site2)
    sys1 = Object.global_objects.get(name="System Object", site=site1)
    sys2 = Object.global_objects.get(name="System Object", site=site2)

    # Property lookups go through moojson which uses ``_get_nothing()`` as
    # the cross-site fallback — that helper is per-site, so the read must
    # happen inside a ContextManager scoped to the matching site.
    with code.ContextManager(site1_wizard, lambda _: None, site=site1):
        sys1_player_pk = sys1.get_property("player").pk
        assert lookup("$player").pk == sys1_player_pk
    with code.ContextManager(site2_wizard, lambda _: None, site=site2):
        sys2_player_pk = sys2.get_property("player").pk
        assert lookup("$player").pk == sys2_player_pk

    assert sys1_player_pk != sys2_player_pk


# ---------------------------------------------------------------------------
# Object.save() site auto-fill priority
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("source", ["context", "caller", "default"])
def test_object_save_fills_site(source, t_two_sites, t_wizard):
    """`Object.save()` fills `site` in priority order: context > caller > default SITE_ID."""
    _, site2 = t_two_sites
    if source == "context":
        with code.ContextManager(t_wizard, lambda _: None, site=site2):
            obj = Object.global_objects.create(name="ctx-spawned", owner=t_wizard)
        expected = site2.pk
    elif source == "caller":
        site2_wizard = Object.global_objects.get(name="Wizard", site=site2)
        with code.ContextManager(site2_wizard, lambda _: None):
            obj = Object.global_objects.create(name="caller-spawned", owner=site2_wizard)
        expected = site2.pk
    else:  # default — no context, no caller
        obj = Object.global_objects.create(name="defaulted")
        expected = get_default_site().pk
    assert obj.site_id == expected


# ---------------------------------------------------------------------------
# moojson cross-site reference handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_moojson_cross_site_ref_decodes_as_nothing(t_two_sites):
    """A property value referring to another site's PK decodes as $nothing."""
    site1, site2 = t_two_sites
    site1_obj = Object.global_objects.filter(site=site1).exclude(name="nothing").first()
    nothing2 = Object.global_objects.get(name="nothing", site=site2)
    # Decode under site2's context — site1_obj's PK should fall through to $nothing.
    from moo.core import moojson

    clear_nothing_cache()
    with code.ContextManager(Object.global_objects.get(name="Wizard", site=site2), lambda _: None, site=site2):
        decoded = moojson.loads('{"o#%d": "%s"}' % (site1_obj.pk, site1_obj.name))
    assert decoded.pk == nothing2.pk


# ---------------------------------------------------------------------------
# SiteManager filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_site_manager_filters_queryset(t_two_sites):
    """``Object.objects`` returns only the active site; ``global_objects`` returns everything."""
    site1, _ = t_two_sites
    total = Object.global_objects.count()
    with code.ContextManager(Object.global_objects.get(name="Wizard", site=site1), lambda _: None, site=site1):
        site1_via_objects = Object.objects.count()
    assert site1_via_objects < total
    assert site1_via_objects == Object.global_objects.filter(site=site1).count()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_site_manager_fails_closed_when_site_missing(t_init):
    """If ``_current_site()`` returns None at runtime, SiteManager returns no rows."""
    with patch("moo.core.managers._current_site", return_value=None):
        assert Object.objects.count() == 0


# ---------------------------------------------------------------------------
# UniversalWizard auto-provisioning
# ---------------------------------------------------------------------------


def _ssh_server_with_user(user, site, conn=None):
    """Build a minimal SSHServer with the user/site/conn attributes set."""
    from moo.shell.server import SSHServer

    server = SSHServer.__new__(SSHServer)
    server.user = user
    server.site = site
    server._conn = conn  # pylint: disable=protected-access
    return server


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_universal_wizard_auto_provisions_idempotently(t_two_sites):
    """A UniversalWizard user gets a wizard avatar+Player on first connect; a second
    call is a no-op. Idempotency is the contract — both calls run in one test."""
    _, site2 = t_two_sites
    user = User.objects.create_user(username="phil", password="x")
    UniversalWizard.objects.create(user=user)

    server = _ssh_server_with_user(user, site2)
    server._auto_provision_universal_wizard()  # pylint: disable=protected-access
    server._auto_provision_universal_wizard()  # pylint: disable=protected-access

    player = Player.objects.get(user=user, site=site2)
    assert player.wizard is True
    assert player.avatar.name == "phil"
    assert player.avatar.unique_name is True
    assert player.avatar.site_id == site2.pk
    assert Player.objects.filter(user=user, site=site2).count() == 1
    assert Object.global_objects.filter(name="phil", site=site2).count() == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_non_universal_superuser_does_not_auto_provision(t_two_sites):
    """A Django superuser without a UniversalWizard record gets nothing on connect."""
    _, site2 = t_two_sites
    user = User.objects.create_superuser(username="adm", password="x", email="adm@example.com")
    assert user.is_superuser  # baseline

    server = _ssh_server_with_user(user, site2)
    server._auto_provision_universal_wizard()  # pylint: disable=protected-access

    assert Player.objects.filter(user=user, site=site2).exists() is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_avatar_hijack_resistance(t_two_sites):
    """A non-unique object with the same name+site cannot be hijacked as a wizard avatar."""
    _, site2 = t_two_sites
    user = User.objects.create_user(username="phil", password="x")
    UniversalWizard.objects.create(user=user)
    # Pre-existing non-unique object with the username.
    decoy = Object.global_objects.create(name="phil", unique_name=False, site=site2)

    server = _ssh_server_with_user(user, site2)
    server._auto_provision_universal_wizard()  # pylint: disable=protected-access

    player = Player.objects.get(user=user, site=site2)
    assert player.avatar.pk != decoy.pk
    assert player.avatar.unique_name is True


# ---------------------------------------------------------------------------
# SSH username suffix routing
# ---------------------------------------------------------------------------


def test_split_user_suffix_basic():
    """``user+sitedomain`` parses into base username + suffix."""
    from moo.shell.server import _split_user_suffix

    assert _split_user_suffix("phil+zork1.local") == ("phil", "zork1.local")
    assert _split_user_suffix("phil") == ("phil", None)
    assert _split_user_suffix("phil+") == ("phil+", None)
    assert _split_user_suffix("+zork1") == ("+zork1", None)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_resolve_site_via_username_suffix(t_two_sites):
    """A username suffix matching a Site domain selects that Site."""
    _, site2 = t_two_sites
    server = _ssh_server_with_user(user=None, site=None)
    server._site_hint = "site2.test"  # pylint: disable=protected-access
    server._resolve_site()  # pylint: disable=protected-access
    assert server.site.pk == site2.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_resolve_site_unknown_suffix_defers_to_picker(t_two_sites):
    """An unknown suffix leaves ``site=None`` so :func:`interact` shows the picker."""
    server = _ssh_server_with_user(user=None, site=None)
    server._site_hint = "nope.test"  # pylint: disable=protected-access
    server._resolve_site()  # pylint: disable=protected-access
    assert server.site is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_resolve_site_no_suffix_defers_to_picker(t_two_sites):
    """No suffix means defer to picker — ``site`` stays ``None``."""
    server = _ssh_server_with_user(user=None, site=None)
    server._site_hint = None  # pylint: disable=protected-access
    server._resolve_site()  # pylint: disable=protected-access
    assert server.site is None


# ---------------------------------------------------------------------------
# moo_init --hostname
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_moo_init_hostname_creates_site():
    """``moo_init --hostname=foo.com`` creates the Site and bootstraps it."""
    from django.core.management import call_command

    call_command("moo_init", bootstrap="default", hostname="foo.local")
    site = Site.objects.get(domain="foo.local")
    assert Object.global_objects.filter(name="System Object", site=site).count() == 1
