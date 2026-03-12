# -*- coding: utf-8 -*-
"""
Tests for moo/core/models/auth.py — Player.
"""

import pytest
from django.contrib.auth import get_user_model

from .. import code, create
from ..models import Object, Player

User = get_user_model()


def _ctx(wizard):
    return code.ContextManager(wizard, lambda m: None)


# ---------------------------------------------------------------------------
# Player creation
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_creation_with_user_and_avatar(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("new avatar")
    user = User.objects.create_user(username="testplayer", password="pw")
    player = Player.objects.create(user=user, avatar=avatar, wizard=False)
    player.refresh_from_db()
    assert player.user == user
    assert player.avatar == avatar
    assert player.wizard is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_creation_without_user(t_init, t_wizard):
    with _ctx(t_wizard):
        avatar = create("npc avatar")
    player = Player.objects.create(user=None, avatar=avatar)
    player.refresh_from_db()
    assert player.user is None
    assert player.avatar == avatar


# ---------------------------------------------------------------------------
# Object.is_player() / is_wizard()
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_player_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("player avatar")
    Player.objects.create(avatar=obj)
    assert obj.is_player()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_player_false(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("not a player")
    assert not obj.is_player()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_wizard_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("wizard avatar")
    Player.objects.create(avatar=obj, wizard=True)
    assert obj.is_wizard()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_wizard_false(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("mortal avatar")
    Player.objects.create(avatar=obj, wizard=False)
    assert not obj.is_wizard()


# ---------------------------------------------------------------------------
# Object.is_connected() is always True
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_is_connected_always_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("conn obj")
    assert obj.is_connected() is True
    # Also true for objects without a Player row
    bare = Object.objects.create(name="bare conn obj")
    assert bare.is_connected() is True
