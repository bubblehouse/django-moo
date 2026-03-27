# -*- coding: utf-8 -*-
"""Tests for the custom allauth SignupForm."""

import pytest
from django.contrib.auth import get_user_model

from moo.core.models import Object, Player
from moo.shell.forms import SignupForm

User = get_user_model()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_valid_form_creates_player_and_avatar(t_init: Object, t_wizard: Object):
    """Valid submission creates a Player linked to a named Object with correct properties."""
    user = User.objects.create_user(username="newplayer", password="pw")
    form = SignupForm(
        data={
            "character_name": "Frobozz",
            "gender": "female",
            "description": "A seasoned adventurer.",
        }
    )
    assert form.is_valid(), form.errors
    form.signup(None, user)

    player = Player.objects.get(user=user)
    avatar = player.avatar
    assert avatar.name == "Frobozz"
    assert avatar.get_property("ps") == "she"
    assert avatar.get_property("po") == "her"
    assert avatar.get_property("description") == "A seasoned adventurer."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gender_pronouns_male(t_init: Object, t_wizard: Object):
    """Male gender sets he/him pronouns."""
    user = User.objects.create_user(username="heroperson", password="pw")
    form = SignupForm(data={"character_name": "Hero", "gender": "male", "description": ""})
    assert form.is_valid()
    form.signup(None, user)

    avatar = Player.objects.get(user=user).avatar
    assert avatar.get_property("ps") == "he"
    assert avatar.get_property("po") == "him"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_gender_pronouns_plural(t_init: Object, t_wizard: Object):
    """Plural gender sets they/them pronouns."""
    user = User.objects.create_user(username="theyperson", password="pw")
    form = SignupForm(data={"character_name": "Sage", "gender": "plural", "description": ""})
    assert form.is_valid()
    form.signup(None, user)

    avatar = Player.objects.get(user=user).avatar
    assert avatar.get_property("ps") == "they"
    assert avatar.get_property("po") == "them"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_description_optional(t_init: Object, t_wizard: Object):
    """Empty description is valid and does not override the inherited default."""
    user = User.objects.create_user(username="nodesc", password="pw")
    form = SignupForm(data={"character_name": "Nameless", "gender": "neuter", "description": ""})
    assert form.is_valid()
    form.signup(None, user)

    avatar = Player.objects.get(user=user).avatar
    # Inherits empty string description from $root_class — no error raised
    assert avatar.get_property("description") == ""


def test_missing_character_name_is_invalid():
    """character_name is required."""
    form = SignupForm(data={"character_name": "", "gender": "plural", "description": ""})
    assert not form.is_valid()
    assert "character_name" in form.errors


def test_invalid_gender_is_invalid():
    """An unrecognised gender value fails ChoiceField validation."""
    form = SignupForm(data={"character_name": "Test", "gender": "alien", "description": ""})
    assert not form.is_valid()
    assert "gender" in form.errors
