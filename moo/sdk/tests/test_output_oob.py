# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for the OOB-related SDK output functions:

- ``send_oob``               raw IAC subnegotiation publish
- ``send_gmcp``              GMCP frame publish (gated on negotiated capability)
- ``play_sound``             GMCP ``Client.Media.Play`` / MSP fallback
- ``room_info_payload``      IRE-style ``Room.Info`` payload builder
- ``_client_supports``       capability lookup with cache fallback
- ``_client_supports_gmcp_package``  GMCP package map lookup
- ``can_open_editor``        rich-mode / GMCP-Editor gating
- ``get_session_setting`` / ``set_session_setting`` / ``get_wrap_column`` /
  ``boot_player`` permission and edge-case branches
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import moo.shell.prompt as prompt_module
from moo.core import code as core_code
from moo.core.exceptions import NoSuchPropertyError, UserError
from moo.sdk import output


def _wizard():
    return SimpleNamespace(is_wizard=lambda: True, pk=1)


def _mortal():
    return SimpleNamespace(is_wizard=lambda: False, pk=2)


@pytest.fixture(autouse=True)
def _clean_session_settings():
    prompt_module._session_settings.clear()
    yield
    prompt_module._session_settings.clear()


# ---------------------------------------------------------------------------
# send_oob
# ---------------------------------------------------------------------------


def test_send_oob_publishes_event_with_bytes_payload():
    """send_oob() emits an ``{"event": "oob", "data": <bytes>}`` to _publish_to_player."""
    obj = MagicMock()
    frame = b"\xff\xfa\xc9Core.Hello\xff\xf0"
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.core._publish_to_player") as pub:
            output.send_oob(obj, frame)
    pub.assert_called_once_with(obj, {"event": "oob", "data": frame})


def test_send_oob_accepts_bytearray_and_normalizes_to_bytes():
    """A ``bytearray`` argument is normalized to ``bytes`` before publish so the queue serialiser is happy."""
    obj = MagicMock()
    frame = bytearray(b"\xff\xfa\xc9hello\xff\xf0")
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.core._publish_to_player") as pub:
            output.send_oob(obj, frame)
    sent = pub.call_args[0][1]["data"]
    assert isinstance(sent, bytes)
    assert sent == bytes(frame)


def test_send_oob_rejects_non_wizard_caller():
    """Non-wizard callers cannot send raw OOB frames."""
    obj = MagicMock()
    with core_code.ContextManager(_mortal(), lambda s: None):
        with pytest.raises(UserError, match="wizards"):
            output.send_oob(obj, b"\xff\xf9")


def test_send_oob_rejects_non_bytes_payload():
    """String / int payloads are rejected before reaching the queue."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with pytest.raises(UserError, match="must be bytes"):
            output.send_oob(obj, "not bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# send_gmcp
# ---------------------------------------------------------------------------


def test_send_gmcp_skips_when_client_did_not_negotiate():
    """If ``_client_supports("gmcp")`` is False, send_gmcp is a no-op (no publish)."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=False):
            with patch("moo.core._publish_to_player") as pub:
                output.send_gmcp(obj, "Char.Vitals", {"hp": 50})
    pub.assert_not_called()


def test_send_gmcp_publishes_oob_frame_when_negotiated():
    """A negotiated client receives an ``IAC SB GMCP <module> <json> IAC SE`` frame."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=True):
            with patch("moo.core._publish_to_player") as pub:
                output.send_gmcp(obj, "Char.Vitals", {"hp": 50, "maxhp": 100})
    msg = pub.call_args[0][1]
    assert msg["event"] == "oob"
    data = msg["data"]
    assert data.startswith(b"\xff\xfa\xc9")  # IAC SB GMCP
    assert data.endswith(b"\xff\xf0")  # IAC SE
    assert b"Char.Vitals" in data
    assert b'{"hp":50,"maxhp":100}' in data


def test_send_gmcp_bare_module_omits_payload():
    """Calling without ``data`` emits the module name only — used for ``Core.Ping`` style events."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=True):
            with patch("moo.core._publish_to_player") as pub:
                output.send_gmcp(obj, "Core.Ping")
    data = pub.call_args[0][1]["data"]
    # No JSON delimiter — the GMCP payload is exactly the module name.
    payload = data[3:-2]  # strip IAC SB GMCP / IAC SE
    assert payload == b"Core.Ping"


def test_send_gmcp_rejects_non_wizard_caller():
    obj = MagicMock()
    with core_code.ContextManager(_mortal(), lambda s: None):
        with pytest.raises(UserError, match="wizards"):
            output.send_gmcp(obj, "Char.Vitals", {})


# ---------------------------------------------------------------------------
# play_sound
# ---------------------------------------------------------------------------


def test_play_sound_uses_gmcp_when_negotiated():
    """When the client speaks GMCP we send ``Client.Media.Play`` rather than the inline marker."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", side_effect=lambda o, c: c == "gmcp"):
            with patch("moo.core._publish_to_player") as pub:
                output.play_sound(obj, "door.wav", volume=70, priority=5)
    data = pub.call_args[0][1]["data"]
    assert b"Client.Media.Play" in data
    assert b'"name":"door.wav"' in data
    assert b'"volume":70' in data
    assert b'"priority":5' in data


def test_play_sound_falls_back_to_msp_marker_when_only_msp():
    """A client that negotiated only MSP gets the inline ``!!SOUND(...)`` marker, not a GMCP frame."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", side_effect=lambda o, c: c == "msp"):
            with patch("moo.core._publish_to_player") as pub:
                output.play_sound(obj, "bell.wav", volume=50, priority=3)
    pub.assert_called_once_with(obj, "!!SOUND(bell.wav V=50 P=3)")


def test_play_sound_no_negotiated_protocol_is_noop():
    """Without GMCP or MSP we publish nothing — vanilla SSH would render the marker as text."""
    obj = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.sdk.output._client_supports", return_value=False):
            with patch("moo.core._publish_to_player") as pub:
                output.play_sound(obj, "door.wav")
    pub.assert_not_called()


def test_play_sound_rejects_non_wizard_caller():
    obj = MagicMock()
    with core_code.ContextManager(_mortal(), lambda s: None):
        with pytest.raises(UserError, match="wizards"):
            output.play_sound(obj, "door.wav")


# ---------------------------------------------------------------------------
# room_info_payload
# ---------------------------------------------------------------------------


def _exit(name, dest_pk=10, aliases=()):
    """Build a fake exit object with the attributes room_info_payload reads."""
    exit_obj = MagicMock()
    exit_obj.name = name
    exit_obj.dest = SimpleNamespace(pk=dest_pk) if dest_pk is not None else None
    alias_objs = [SimpleNamespace(alias=a) for a in aliases]
    exit_obj.aliases.all.return_value = alias_objs
    return exit_obj


def test_room_info_payload_maps_cardinal_directions_to_short_codes():
    """``"north"`` becomes ``"n"``, ``"northeast"`` → ``"ne"``, etc."""
    room = MagicMock()
    room.pk = 7
    room.name = "Town Square"
    room.get_property_objects.return_value = [
        _exit("north", dest_pk=8),
        _exit("northeast", dest_pk=9),
        _exit("up", dest_pk=10),
    ]
    payload = output.room_info_payload(room)
    assert payload == {"num": "7", "name": "Town Square", "exits": {"n": "8", "ne": "9", "u": "10"}}


def test_room_info_payload_handles_first_word_match_for_compound_names():
    """DjangoMOO names exits ``"east from grand foyer"`` — the first word is the direction."""
    room = MagicMock()
    room.pk = 12
    room.name = "Grand Foyer"
    room.get_property_objects.return_value = [_exit("east from grand foyer", dest_pk=13)]
    payload = output.room_info_payload(room)
    assert payload["exits"] == {"e": "13"}


def test_room_info_payload_uses_alias_when_name_does_not_match():
    """Custom-named exits still get a short code via their alias list."""
    room = MagicMock()
    room.pk = 1
    room.name = "Hidden Lab"
    room.get_property_objects.return_value = [_exit("trapdoor", dest_pk=2, aliases=["down", "d"])]
    payload = output.room_info_payload(room)
    assert payload["exits"] == {"d": "2"}


def test_room_info_payload_falls_back_to_raw_name_for_unknown_directions():
    """Custom non-cardinal exits round-trip unchanged so the client still renders them."""
    room = MagicMock()
    room.pk = 3
    room.name = "Wizard's Tower"
    room.get_property_objects.return_value = [_exit("portal", dest_pk=4)]
    payload = output.room_info_payload(room)
    assert payload["exits"] == {"portal": "4"}


def test_room_info_payload_skips_exits_with_no_destination():
    """Exits that have no ``dest`` (broken / not yet linked) are silently dropped from the map."""
    room = MagicMock()
    room.pk = 5
    room.name = "Hallway"
    room.get_property_objects.return_value = [
        _exit("north", dest_pk=6),
        _exit("south", dest_pk=None),
    ]
    payload = output.room_info_payload(room)
    assert payload["exits"] == {"n": "6"}


def test_room_info_payload_swallows_attribute_error_on_aliases():
    """Some exit objects lack an aliases manager; that branch must not crash payload generation."""
    bad_exit = MagicMock()
    bad_exit.name = "weird"
    bad_exit.dest = SimpleNamespace(pk=9)
    bad_exit.aliases = SimpleNamespace()  # no .all() — accessing it raises AttributeError
    room = MagicMock()
    room.pk = 99
    room.name = "Test Room"
    room.get_property_objects.return_value = [bad_exit]
    payload = output.room_info_payload(room)
    assert payload["exits"] == {"weird": "9"}


def test_room_info_payload_handles_room_with_no_exits():
    """A room with no exits property returns an empty exits dict, not a crash."""
    room = MagicMock()
    room.pk = 100
    room.name = "The Void"
    room.get_property_objects.return_value = None
    payload = output.room_info_payload(room)
    assert payload == {"num": "100", "name": "The Void", "exits": {}}


# ---------------------------------------------------------------------------
# _client_supports / _client_supports_gmcp_package
# ---------------------------------------------------------------------------


def _patch_player_lookup(user_pk):
    """Patch ``Player.objects.filter(...).select_related(...).first()`` to return a stub."""
    if user_pk is None:
        result = None
    else:
        result = SimpleNamespace(user=SimpleNamespace(pk=user_pk))
    qs = MagicMock()
    qs.select_related.return_value.first.return_value = result
    manager = MagicMock()
    manager.filter.return_value = qs
    return patch("moo.core.models.auth.Player.objects", manager)


def test_client_supports_returns_false_when_no_player_avatar():
    """A non-player ``obj`` (Generic Thing, etc.) yields False without raising."""
    with _patch_player_lookup(None):
        assert output._client_supports(MagicMock(), "gmcp") is False


def test_client_supports_reads_in_process_session_settings():
    """The hot path is the in-process dict — no cache hit needed when the SSH server populated it."""
    user_pk = 4711
    prompt_module._session_settings[user_pk] = {"iac": {"gmcp": True, "msp": False}}
    with _patch_player_lookup(user_pk):
        assert output._client_supports(MagicMock(), "gmcp") is True
        assert output._client_supports(MagicMock(), "msp") is False
        assert output._client_supports(MagicMock(), "eor") is False


def test_client_supports_falls_back_to_django_cache_for_celery_workers():
    """In Celery the SSH server's ``_session_settings`` is empty; the cache mirror is the fallback."""
    user_pk = 4712
    fake_cache = {f"moo:session:{user_pk}:iac": {"gmcp": True, "mssp": True}}
    with _patch_player_lookup(user_pk):
        with patch("django.core.cache.cache.get", side_effect=fake_cache.get):
            assert output._client_supports(MagicMock(), "gmcp") is True
            assert output._client_supports(MagicMock(), "mssp") is True
            assert output._client_supports(MagicMock(), "msp") is False


def test_client_supports_gmcp_package_returns_false_for_none_obj():
    """Defensive guard for callers that may pass ``None`` (e.g. ``can_open_editor`` with no player)."""
    assert output._client_supports_gmcp_package(None, "Editor") is False


def test_client_supports_gmcp_package_reads_packages_dict():
    """The GMCP package map is keyed by package name; presence-only (we ignore the version int)."""
    user_pk = 4713
    prompt_module._session_settings[user_pk] = {"iac": {"gmcp_packages": {"Editor": 1, "Char": 1}}}
    with _patch_player_lookup(user_pk):
        assert output._client_supports_gmcp_package(MagicMock(), "Editor") is True
        assert output._client_supports_gmcp_package(MagicMock(), "Room") is False


def test_client_supports_gmcp_package_falls_back_to_cache():
    """Cross-process: Celery workers read the cache-mirrored package map when in-process is empty."""
    user_pk = 4714
    fake_cache = {f"moo:session:{user_pk}:iac": {"gmcp_packages": {"Editor": 1}}}
    with _patch_player_lookup(user_pk):
        with patch("django.core.cache.cache.get", side_effect=fake_cache.get):
            assert output._client_supports_gmcp_package(MagicMock(), "Editor") is True


# ---------------------------------------------------------------------------
# can_open_editor
# ---------------------------------------------------------------------------


def test_can_open_editor_true_in_rich_mode():
    """Rich-mode (prompt_toolkit TUI) sessions can always show the editor."""
    with patch("moo.sdk.output.get_client_mode", return_value="rich"):
        assert output.can_open_editor() is True


def test_can_open_editor_true_in_raw_mode_when_client_advertises_editor_package():
    """Raw-mode clients with the GMCP ``Editor`` package can still open the editor (Mudlet bridge path)."""
    with patch("moo.sdk.output.get_client_mode", return_value="raw"):
        with patch("moo.sdk.output._client_supports_gmcp_package", return_value=True):
            assert output.can_open_editor() is True


def test_can_open_editor_false_in_raw_mode_without_gmcp_editor_package():
    """Raw-mode without the bridge falls back to the inline ``with "..."`` form — editor unavailable."""
    with patch("moo.sdk.output.get_client_mode", return_value="raw"):
        with patch("moo.sdk.output._client_supports_gmcp_package", return_value=False):
            assert output.can_open_editor() is False


# ---------------------------------------------------------------------------
# get_session_setting / set_session_setting edge cases
# ---------------------------------------------------------------------------


def test_get_session_setting_returns_default_when_no_player_in_context():
    """Outside of a verb context (no ``context.player``) the default is returned."""
    assert output.get_session_setting("any_key", default="fallback") == "fallback"


def test_set_session_setting_noop_outside_player_context():
    """No player → no cache write, no publish — but no exception either."""
    with patch("moo.core._publish_to_player") as pub:
        output.set_session_setting("any_key", "any_value")
    pub.assert_not_called()


# ---------------------------------------------------------------------------
# get_wrap_column edge cases
# ---------------------------------------------------------------------------


def test_get_wrap_column_returns_terminal_width_when_property_missing():
    """No ``wrap_column`` property → fall through to the terminal width session setting."""
    player = MagicMock()
    player.get_property.side_effect = NoSuchPropertyError("wrap_column")
    prompt_module._session_settings[9001] = {"terminal_width": 132}
    with _patch_player_lookup(9001):
        with patch.object(core_code.ContextManager, "get", side_effect=lambda k: player if k == "player" else None):
            assert output.get_wrap_column() == 132


def test_get_wrap_column_honors_explicit_integer_property():
    """A non-auto integer wrap_column overrides the terminal width."""
    player = MagicMock()
    player.get_property.return_value = "72"
    with patch.object(core_code.ContextManager, "get", side_effect=lambda k: player if k == "player" else None):
        assert output.get_wrap_column() == 72


def test_get_wrap_column_falls_back_to_80_for_unparseable_property():
    """A garbage wrap_column (non-numeric, non-auto) falls back to the 80-column default."""
    player = MagicMock()
    player.get_property.return_value = "abc"
    with patch.object(core_code.ContextManager, "get", side_effect=lambda k: player if k == "player" else None):
        assert output.get_wrap_column() == 80


# ---------------------------------------------------------------------------
# boot_player permission branch
# ---------------------------------------------------------------------------


def test_boot_player_rejects_non_wizard_booting_someone_else():
    """A mortal can boot themselves (handled elsewhere) but not other players."""
    target = MagicMock()
    caller = SimpleNamespace(is_wizard=lambda: False, pk=42)
    target.__ne__ = lambda self, other: True  # not equal to caller
    with core_code.ContextManager(caller, lambda s: None):
        with pytest.raises(UserError, match="wizards"):
            output.boot_player(target)


def test_boot_player_publishes_disconnect_event_for_wizard():
    """Wizards may boot anyone; a ``disconnect`` event is queued for the target."""
    target = MagicMock()
    with core_code.ContextManager(_wizard(), lambda s: None):
        with patch("moo.core._publish_to_player") as pub:
            output.boot_player(target)
    pub.assert_called_once_with(target, {"event": "disconnect"})
