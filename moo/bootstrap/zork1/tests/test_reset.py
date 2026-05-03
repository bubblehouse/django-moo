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
def test_save_state_excludes_player_zstate_properties(t_init, t_wizard, tmp_path):
    """zstate_* properties on Player avatars are excluded from the snapshot."""
    t_wizard.set_property("zstate_score", 99)
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    # The Wizard avatar's zstate_* must not be in the fixture — it's per-player game state.
    wizard_pk = t_wizard.pk
    prop_rows = [row for row in data if row.get("model") == "core.property"]
    wizard_zstate = [
        r for r in prop_rows if r["fields"].get("origin") == wizard_pk and r["fields"]["name"].startswith("zstate_")
    ]
    assert not wizard_zstate


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_save_state_includes_world_zstate_properties(t_init, t_wizard, tmp_path):
    """zstate_* properties on world objects (e.g. ZIL tables on $zil_sdk) ARE saved."""
    zil_sdk = lookup("ZIL SDK")
    zil_sdk.set_property("zstate_hero_melee", ["punch", "kick", "headbutt"])
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    prop_rows = [row for row in data if row.get("model") == "core.property"]
    world_zstate = [
        r for r in prop_rows if r["fields"].get("origin") == zil_sdk.pk and r["fields"]["name"] == "zstate_hero_melee"
    ]
    assert len(world_zstate) == 1, "Bootstrap-level zstate_* (ZIL tables) must survive snapshot"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
def test_save_state_strips_site_id(t_init, tmp_path):
    """Object rows in the fixture have no site_id, so the dump is portable."""
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    object_rows = [row for row in data if row.get("model") == "core.object"]
    assert object_rows, "fixture must contain at least one object row"
    assert all("site" not in r["fields"] for r in object_rows)


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
    """moo_reset removes zstate_* properties from player avatars."""
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
def test_reset_preserves_world_zstate(t_init, t_wizard, tmp_path):
    """moo_reset must NOT clear zstate_* on non-player world objects.

    Bootstrap-level ZIL tables (e.g. on $zil_sdk) live in the zstate_*
    namespace; clearing them would force a follow-up moo_init --sync to
    rebuild them.
    """
    zil_sdk = lookup("ZIL SDK")
    zil_sdk.set_property("zstate_hero_melee", ["punch", "kick"])
    fixture_path = str(tmp_path / "world_state.json")
    call_command("moo_save_state", bootstrap="zork1", output=fixture_path)

    # Player has dirty state; SDK keeps its table.
    t_wizard.set_property("zstate_score", 50)
    call_command("moo_reset", bootstrap="zork1", fixture=fixture_path)

    # Player state was cleared.
    with pytest.raises(NoSuchPropertyError):
        t_wizard.get_property("zstate_score")
    # SDK table survives.
    assert zil_sdk.get_property("zstate_hero_melee") == ["punch", "kick"]


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
