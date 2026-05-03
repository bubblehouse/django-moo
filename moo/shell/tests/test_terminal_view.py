# -*- coding: utf-8 -*-
"""Tests for the terminal() POST proxy that injects the site suffix from Host."""

import json
from unittest.mock import patch

import pytest
from django.contrib.sites.models import Site
from django.test import override_settings
from django.urls import reverse


def _fake_urlopen_capture(captured: list):
    """Return a urlopen replacement that records the forwarded request and replies 200."""

    class _FakeResp:
        status = 200

        def read(self):
            return b'{"id": "fake"}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _urlopen(req, timeout=None):  # pylint: disable=unused-argument
        captured.append(req.data.decode())
        return _FakeResp()

    return _urlopen


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_terminal_post_injects_site_suffix_from_host(client):
    """Browser hitting zork1.local has its SSH username rewritten to ``user+zork1.local``."""
    Site.objects.get_or_create(domain="zork1.local", defaults={"name": "zork1.local"})
    captured: list = []
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen_capture(captured)):
        client.post(
            reverse("terminal"),
            data={"username": "phil", "password": "x", "hostname": "shell", "port": "8022"},
            HTTP_HOST="zork1.local",
        )
    assert captured, "POST proxy never reached urlopen"
    assert "username=phil%2Bzork1.local" in captured[0]


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_terminal_post_does_not_inject_when_host_unknown(client):
    """A Host header with no matching Site leaves the username unchanged."""
    captured: list = []
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen_capture(captured)):
        client.post(
            reverse("terminal"),
            data={"username": "phil", "password": "x", "hostname": "shell", "port": "8022"},
            HTTP_HOST="nope.test",
        )
    assert captured
    assert "username=phil&" in captured[0] or captured[0].endswith("username=phil")


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_terminal_post_preserves_existing_suffix(client):
    """A user-supplied suffix is not double-encoded."""
    Site.objects.get_or_create(domain="zork1.local", defaults={"name": "zork1.local"})
    captured: list = []
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen_capture(captured)):
        client.post(
            reverse("terminal"),
            data={"username": "phil+other.local", "password": "x", "hostname": "shell", "port": "8022"},
            HTTP_HOST="zork1.local",
        )
    assert captured
    assert "username=phil%2Bother.local" in captured[0]
