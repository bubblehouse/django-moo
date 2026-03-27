# -*- coding: utf-8 -*-
"""Tests for the custom SignupView that allows already-authenticated users to re-register."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from moo.core.models import Object, Player

User = get_user_model()

SIGNUP_URL = reverse("account_signup")

VALID_POST_DATA = {
    "username": "newcomer",
    "email": "newcomer@example.com",
    "password1": "str0ng-passw0rd!",
    "password2": "str0ng-passw0rd!",
    "character_name": "Newcomer",
    "gender": "plural",
    "description": "",
}


@pytest.mark.django_db
def test_signup_get_anonymous(client):
    """An anonymous user can reach the signup page."""
    response = client.get(SIGNUP_URL)
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_signup_get_authenticated_shows_form(t_init: Object, client):
    """An authenticated user is logged out and shown the signup form rather than redirected."""
    user = User.objects.create_user(username="existing", password="pw")
    client.force_login(user)

    response = client.get(SIGNUP_URL)

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_signup_post_authenticated_logs_out_old_user(t_init: Object, client):
    """Submitting signup while authenticated ends the old session."""
    existing = User.objects.create_user(username="existing", password="pw")
    client.force_login(existing)

    client.post(SIGNUP_URL, VALID_POST_DATA)

    # The old user's session must be gone.
    assert client.session.get("_auth_user_id") != str(existing.pk)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_signup_post_authenticated_creates_new_account(t_init: Object, client):
    """Submitting signup while authenticated creates the new Player and avatar."""
    existing = User.objects.create_user(username="existing", password="pw")
    client.force_login(existing)

    client.post(SIGNUP_URL, VALID_POST_DATA)

    new_user = User.objects.get(username="newcomer")
    player = Player.objects.get(user=new_user)
    assert player.avatar.name == "Newcomer"
