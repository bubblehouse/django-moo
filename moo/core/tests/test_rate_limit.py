"""Tests for the per-account broadcast flood limit (spec 200, item F)."""

import warnings

import pytest
from django.core.cache import cache

from .. import code
from .. import _publish_to_player
from ..models import Object
from ...sdk import lookup, broadcast_allowed, broadcast_limit


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_broadcast_allowed_counts_within_window(settings):
    settings.MOO_BROADCAST_RATE_LIMIT = 2
    settings.MOO_BROADCAST_RATE_WINDOW = 60
    cache.clear()
    assert broadcast_allowed(42) is True  # 1
    assert broadcast_allowed(42) is True  # 2
    assert broadcast_allowed(42) is False  # 3 — over budget
    # A different account has an independent budget.
    assert broadcast_allowed(99) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_broadcast_disabled_never_throttles(settings):
    settings.MOO_BROADCAST_RATE_LIMIT = 0
    cache.clear()
    for _ in range(100):
        assert broadcast_allowed(7) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_flood_to_others_is_dropped(settings, t_init: Object, t_wizard: Object):
    """Broadcast lines beyond the budget are dropped (the $spew backstop)."""
    settings.MOO_BROADCAST_RATE_LIMIT = 3
    settings.MOO_BROADCAST_RATE_WINDOW = 60
    cache.clear()
    with code.ContextManager(t_wizard, lambda _: None):
        player = lookup("Player")
    # Initiator is the (non-wizard) player; recipient is someone else (the wizard).
    with code.ContextManager(t_wizard, lambda _: None, player=player):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for i in range(6):
                _publish_to_player(t_wizard, f"spam {i}")
    delivered = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert len(delivered) == 3


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_own_output_is_never_charged(settings, t_init: Object, t_wizard: Object):
    """A player's own output (recipient == initiator) is exempt — verbosity is fine."""
    settings.MOO_BROADCAST_RATE_LIMIT = 3
    settings.MOO_BROADCAST_RATE_WINDOW = 60
    cache.clear()
    with code.ContextManager(t_wizard, lambda _: None, player=t_wizard):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for i in range(6):
                _publish_to_player(t_wizard, f"line {i}")  # recipient == initiator
    delivered = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert len(delivered) == 6


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_sys_knob_overrides_setting(settings, t_init: Object, t_wizard: Object):
    settings.MOO_BROADCAST_RATE_LIMIT = 100
    cache.clear()
    with code.ContextManager(t_wizard, lambda _: None):
        sys_obj = Object.global_objects.get(pk=1)
        sys_obj.set_property("broadcast_rate_limit", 2)
        assert broadcast_limit() == 2
