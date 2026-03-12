# -*- coding: utf-8 -*-
"""
Tests for connected_players() in moo/core/__init__.py.
"""

from datetime import datetime, timedelta, timezone

import pytest

from .. import code, connected_players, create
from ..models import Player


def _ctx(wizard):
    return code.ContextManager(wizard, lambda m: None)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_connected_players_includes_recent(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("Online Player")
    Player.objects.create(avatar=avatar)
    with _ctx(t_wizard):
        avatar.set_property("last_connected_time", datetime.now(timezone.utc))
    with _ctx(t_wizard):
        result = connected_players()
    assert avatar in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_connected_players_excludes_stale(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("Offline Player")
    Player.objects.create(avatar=avatar)
    stale = datetime.now(timezone.utc) - timedelta(minutes=10)
    with _ctx(t_wizard):
        avatar.set_property("last_connected_time", stale)
    with _ctx(t_wizard):
        result = connected_players()
    assert avatar not in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_connected_players_custom_window(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("Recent Player")
    Player.objects.create(avatar=avatar)
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    with _ctx(t_wizard):
        avatar.set_property("last_connected_time", ten_min_ago)
    with _ctx(t_wizard):
        result = connected_players(within=timedelta(hours=1))
    assert avatar in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_connected_players_excludes_non_players(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("Not A Player")
        obj.set_property("last_connected_time", datetime.now(timezone.utc))
    with _ctx(t_wizard):
        result = connected_players()
    assert obj not in result


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_connected_players_precaches_property(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("Cached Player")
    Player.objects.create(avatar=avatar)
    now = datetime.now(timezone.utc)
    with _ctx(t_wizard):
        avatar.set_property("last_connected_time", now)

    ctx = _ctx(t_wizard)
    with ctx:
        connected_players()
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert (avatar.pk, "last_connected_time", True) in pcache
        cached_value = pcache[(avatar.pk, "last_connected_time", True)]
    assert cached_value == now
