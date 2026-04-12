"""
Tests for the moo_save_state and moo_reset management commands.
"""

import json

import pytest
from django.core.management import call_command
from moo.sdk import lookup, create, NoSuchPropertyError


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_save_state_creates_fixture(t_init, t_wizard, tmp_path):
    """moo_save_state writes a valid JSON fixture file."""
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_save_state_excludes_zstate_properties(t_init, t_wizard, tmp_path):
    """The fixture does not include zstate_* properties."""
    t_wizard.set_property("zstate_score", 99)
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    prop_names = [row["fields"].get("name", "") for row in data if "property" in row.get("model", "").lower()]
    assert not any(name.startswith("zstate_") for name in prop_names)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_reset_restores_object_location(t_init, t_wizard, tmp_path):
    """After a player moves an object, moo_reset restores its original location."""
    zork_thing = lookup("Zork Thing")
    room = create("Reset Test Room", parents=[lookup("Zork Room")])
    coin = create("reset coin", parents=[zork_thing])
    coin.location = room
    coin.save()

    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    # Player picks up the coin
    coin.location = t_wizard
    coin.save()
    coin.refresh_from_db()
    assert coin.location == t_wizard

    # Reset
    call_command("moo_reset", bootstrap="zork1", fixture=fixture_path)
    coin.refresh_from_db()
    assert coin.location == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_reset_clears_player_zstate(t_init, t_wizard, tmp_path):
    """moo_reset removes zstate_* properties from player objects."""
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    t_wizard.set_property("zstate_cyclops_flag", True)
    call_command("moo_reset", bootstrap="zork1", fixture=fixture_path)

    try:
        t_wizard.get_property("zstate_cyclops_flag")
        assert False, "zstate_cyclops_flag should have been cleared"
    except NoSuchPropertyError:
        pass


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_reset_keeps_player_account(t_init, t_wizard, tmp_path):
    """moo_reset does not delete the player object itself."""
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)
    call_command("moo_reset", bootstrap="zork1", fixture=fixture_path)

    wizard = lookup("Wizard")
    assert wizard is not None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_reset_keep_player_state_flag(t_init, t_wizard, tmp_path):
    """--keep-player-state preserves zstate_* properties after reset."""
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    t_wizard.set_property("zstate_score", 99)
    call_command("moo_reset", bootstrap="zork1", fixture=fixture_path, keep_player_state=True)

    assert t_wizard.get_property("zstate_score") == 99
