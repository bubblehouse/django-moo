"""
Unit tests for the $zork_sdk verb files.
"""

import pytest
from moo.core import code
from moo.sdk import lookup, create


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_zstate_set_and_get(t_init, t_wizard):
    """Round-trip: set a zstate value and read it back."""
    zork_sdk = lookup("Zork SDK")
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("zstate_set", "TEST-KEY", 42)
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("zstate_get", "TEST-KEY")
    assert result == 42


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_zstate_get_missing_returns_none(t_init, t_wizard):
    """Missing zstate key returns None."""
    zork_sdk = lookup("Zork SDK")
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("zstate_get", "NONEXISTENT-KEY")
    assert result is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_zstate_key_conversion(t_init, t_wizard):
    """UPPER-KEBAB-CASE key is stored as zstate_lower_snake_case on the player."""
    zork_sdk = lookup("Zork SDK")
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("zstate_set", "CYCLOPS-FLAG", True)
    assert t_wizard.get_property("zstate_cyclops_flag") is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_flag_default_false_for_missing_property(t_init, t_wizard):
    """flag() returns False when the property doesn't exist."""
    zork_sdk = lookup("Zork SDK")
    obj = create("test coin", parents=[lookup("Zork Thing")])
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("flag", obj, "nonexistent_flag")
    assert result is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_set_flag_and_read_back(t_init, t_wizard):
    """set_flag() stores a bool; flag() reads it back."""
    zork_sdk = lookup("Zork SDK")
    obj = create("test box", parents=[lookup("Zork Thing")])
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("set_flag", obj, "open", True)
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("flag", obj, "open")
    assert result is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_desc_returns_description_property(t_init, t_wizard):
    """desc() returns the object's description property."""
    zork_sdk = lookup("Zork SDK")
    obj = create("shiny coin", parents=[lookup("Zork Thing")])
    obj.set_property("description", "A shiny coin.")
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("desc", obj)
    assert result == "A shiny coin."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_desc_falls_back_to_name(t_init, t_wizard):
    """desc() falls back to obj.name when no description property exists."""
    zork_sdk = lookup("Zork SDK")
    obj = create("plain rock", parents=[lookup("Zork Thing")])
    with code.ContextManager(t_wizard, [].append):
        result = zork_sdk.invoke_verb("desc", obj)
    assert result == obj.name


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_move_changes_location(t_init, t_wizard):
    """move() changes the object's location."""
    zork_sdk = lookup("Zork SDK")
    obj = create("pebble", parents=[lookup("Zork Thing")])
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("move", obj, t_wizard)
    obj.refresh_from_db()
    assert obj.location == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_remove_sets_location_none(t_init, t_wizard):
    """remove() sets the object's location to None."""
    zork_sdk = lookup("Zork SDK")
    obj = create("loose stone", parents=[lookup("Zork Thing")])
    obj.location = t_wizard
    obj.save()
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("remove", obj)
    obj.refresh_from_db()
    assert obj.location is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_jigs_up_moves_player_to_start(t_init, t_wizard):
    """jigs_up() moves context.player to player_start on $zork_sdk."""
    zork_sdk = lookup("Zork SDK")
    start_room = create("Start Room", parents=[lookup("Zork Root")])
    zork_sdk.set_property("player_start", start_room)
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        zork_sdk.invoke_verb("jigs_up", "You fell into the pit.")
    t_wizard.refresh_from_db()
    assert t_wizard.location == start_room
    assert any("You fell into the pit." in p for p in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_score_update_increments(t_init, t_wizard):
    """score_update() adds to zstate_score on context.player."""
    zork_sdk = lookup("Zork SDK")
    t_wizard.set_property("zstate_score", 0)
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("score_update", 10)
    assert t_wizard.get_property("zstate_score") == 10


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_queue_adds_entry(t_init, t_wizard):
    """queue() adds a turn-timed entry to zstate_queue on context.player."""
    zork_sdk = lookup("Zork SDK")
    t_wizard.set_property("zstate_queue", [])
    t_wizard.set_property("zstate_moves", 5)
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("queue", "i-candles", 3)
    q = t_wizard.get_property("zstate_queue")
    assert len(q) == 1
    assert q[0]["name"] == "i-candles"
    assert q[0]["fire_at_turn"] == 8  # 5 + 3


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_cancel_removes_entry(t_init, t_wizard):
    """cancel() removes matching entry from zstate_queue."""
    zork_sdk = lookup("Zork SDK")
    t_wizard.set_property("zstate_queue", [{"name": "i-candles", "fire_at_turn": 10}])
    with code.ContextManager(t_wizard, [].append):
        zork_sdk.invoke_verb("cancel", "i-candles")
    q = t_wizard.get_property("zstate_queue")
    assert q == []
