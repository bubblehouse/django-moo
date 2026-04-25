# -*- coding: utf-8 -*-
"""
IAC parser, encoder, and negotiator tests.

Covers the wire format for every protocol the shell actually speaks
(GMCP, MSSP, MTTS/TTYPE, CHARSET, MSP, GA/EOR) plus the negotiator's
option-state machine.
"""

import pytest

from moo.shell.iac import (
    DO,
    DONT,
    EOR,
    GA,
    IAC,
    MSSP_VAL,
    MSSP_VAR,
    MTTS_ANSI,
    MTTS_SCREEN_READER,
    MTTS_UTF8,
    OPT_CHARSET,
    OPT_GMCP,
    OPT_MSSP,
    OPT_NAWS,
    OPT_SGA,
    OPT_TTYPE,
    SB,
    SE,
    TTYPE_IS,
    WILL,
    WONT,
    IacNegotiator,
    IacParser,
    encode_charset_accepted,
    encode_cmd,
    encode_gmcp,
    encode_mssp,
    encode_sb,
    encode_ttype_send,
    is_known_mud_client,
    msp_sound_marker,
    parse_gmcp,
    parse_mtts_bitfield,
    parse_ttype_is,
)

# ---------------------------------------------------------------------------
# IacParser — byte-feed state machine
# ---------------------------------------------------------------------------


def test_parser_plain_text_passes_through():
    parser = IacParser()
    events, residual = parser.feed(b"hello\r\n")
    assert not events
    assert residual == b"hello\r\n"


def test_parser_simple_cmd_will_opt():
    parser = IacParser()
    events, residual = parser.feed(bytes((IAC, WILL, OPT_TTYPE)))
    assert events == [("cmd", WILL, OPT_TTYPE)]
    assert residual == b""


def test_parser_cmd_mixed_with_text():
    parser = IacParser()
    frame = b"hi" + bytes((IAC, DO, OPT_GMCP)) + b"!"
    events, residual = parser.feed(frame)
    assert events == [("cmd", DO, OPT_GMCP)]
    assert residual == b"hi!"


def test_parser_escaped_iac_in_text_is_literal_ff():
    """IAC IAC in a non-subneg context is a literal 0xFF in the user stream."""
    parser = IacParser()
    events, residual = parser.feed(bytes((ord("a"), IAC, IAC, ord("b"))))
    assert not events
    assert residual == bytes((ord("a"), 0xFF, ord("b")))


def test_parser_subneg_frame():
    parser = IacParser()
    frame = bytes((IAC, SB, OPT_GMCP)) + b"Core.Hello {}" + bytes((IAC, SE))
    events, residual = parser.feed(frame)
    assert events == [("sb", OPT_GMCP, b"Core.Hello {}")]
    assert residual == b""


def test_parser_subneg_with_escaped_iac_in_payload():
    """IAC IAC inside an SB payload is a literal 0xFF byte."""
    parser = IacParser()
    frame = bytes((IAC, SB, OPT_MSSP)) + bytes((IAC, IAC)) + b" data" + bytes((IAC, SE))
    events, residual = parser.feed(frame)
    assert events == [("sb", OPT_MSSP, b"\xff data")]
    assert residual == b""


def test_parser_partial_subneg_across_feeds():
    """Split an IAC SB ... IAC SE frame across three feed() calls."""
    parser = IacParser()
    frame = bytes((IAC, SB, OPT_GMCP)) + b"Core.Hello {}" + bytes((IAC, SE))
    events1, r1 = parser.feed(frame[:3])  # IAC SB GMCP
    events2, r2 = parser.feed(frame[3:10])  # partial payload
    events3, r3 = parser.feed(frame[10:])  # rest + IAC SE
    assert not events1
    assert not events2
    assert events3 == [("sb", OPT_GMCP, b"Core.Hello {}")]
    assert r1 == r2 == r3 == b""


def test_parser_partial_cmd_across_feeds():
    parser = IacParser()
    events1, _ = parser.feed(bytes((IAC,)))
    events2, _ = parser.feed(bytes((WILL,)))
    events3, _ = parser.feed(bytes((OPT_GMCP,)))
    assert not events1
    assert not events2
    assert events3 == [("cmd", WILL, OPT_GMCP)]


def test_parser_ga_event():
    parser = IacParser()
    events, residual = parser.feed(bytes((IAC, GA)))
    assert events == [("ga",)]
    assert residual == b""


def test_parser_eor_event():
    parser = IacParser()
    events, residual = parser.feed(bytes((IAC, EOR)))
    assert events == [("eor",)]
    assert residual == b""


def test_parser_multiple_events_one_feed():
    parser = IacParser()
    frame = (
        bytes((IAC, WILL, OPT_TTYPE))
        + b"text"
        + bytes((IAC, DO, OPT_GMCP))
        + bytes((IAC, SB, OPT_GMCP))
        + b"Core.Hello"
        + bytes((IAC, SE))
    )
    events, residual = parser.feed(frame)
    assert events == [
        ("cmd", WILL, OPT_TTYPE),
        ("cmd", DO, OPT_GMCP),
        ("sb", OPT_GMCP, b"Core.Hello"),
    ]
    assert residual == b"text"


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------


def test_encode_cmd_produces_iac_triple():
    assert encode_cmd(WILL, OPT_GMCP) == bytes((IAC, WILL, OPT_GMCP))
    assert encode_cmd(DO, OPT_TTYPE) == bytes((IAC, DO, OPT_TTYPE))


def test_encode_sb_doubles_iac_in_payload():
    """An 0xFF byte inside an SB payload must be doubled to (IAC, IAC)."""
    out = encode_sb(OPT_MSSP, b"\xff payload")
    assert out == bytes((IAC, SB, OPT_MSSP, IAC, IAC)) + b" payload" + bytes((IAC, SE))


def test_sb_round_trip_through_parser():
    payload = b"arbitrary\x00\x01\xff\xfe bytes"
    frame = encode_sb(OPT_GMCP, payload)
    parser = IacParser()
    events, residual = parser.feed(frame)
    assert events == [("sb", OPT_GMCP, payload)]
    assert residual == b""


# ---------------------------------------------------------------------------
# GMCP
# ---------------------------------------------------------------------------


def test_encode_gmcp_with_data():
    out = encode_gmcp("Core.Hello", {"name": "DjangoMOO", "version": "1.3.0"})
    assert out.startswith(bytes((IAC, SB, OPT_GMCP)))
    assert out.endswith(bytes((IAC, SE)))
    payload = out[3:-2]
    assert payload == b'Core.Hello {"name":"DjangoMOO","version":"1.3.0"}'


def test_encode_gmcp_bare_module():
    out = encode_gmcp("Client.Ping", None)
    assert out == bytes((IAC, SB, OPT_GMCP)) + b"Client.Ping" + bytes((IAC, SE))


def test_parse_gmcp_round_trip():
    data = {"hp": 50, "maxhp": 100}
    frame = encode_gmcp("Char.Vitals", data)
    parser = IacParser()
    events, _ = parser.feed(frame)
    assert len(events) == 1
    _, opt, payload = events[0]
    assert opt == OPT_GMCP
    module, parsed = parse_gmcp(payload)
    assert module == "Char.Vitals"
    assert parsed == data


def test_parse_gmcp_bare_module():
    module, data = parse_gmcp(b"Core.Ping")
    assert module == "Core.Ping"
    assert data is None


# ---------------------------------------------------------------------------
# TTYPE / MTTS
# ---------------------------------------------------------------------------


def test_encode_ttype_send():
    assert encode_ttype_send() == bytes((IAC, SB, OPT_TTYPE, 1, IAC, SE))


def test_parse_ttype_is_extracts_name():
    assert parse_ttype_is(bytes((TTYPE_IS,)) + b"Mudlet 4.15") == "Mudlet 4.15"


def test_parse_ttype_is_rejects_wrong_tag():
    with pytest.raises(ValueError):
        parse_ttype_is(b"\x01Mudlet")  # 0x01 is SEND, not IS


def test_parse_mtts_bitfield_extracts_integer():
    assert parse_mtts_bitfield("MTTS 1") == 1
    assert parse_mtts_bitfield("MTTS 447") == 447
    assert parse_mtts_bitfield("XTERM") == 0
    assert parse_mtts_bitfield("MTTS garbage") == 0


def test_is_known_mud_client_matches_major_clients():
    assert is_known_mud_client("Mudlet 4.15.1")
    assert is_known_mud_client("MUSHclient")
    assert is_known_mud_client("TINTIN++")


def test_is_known_mud_client_rejects_ordinary_terminals():
    assert not is_known_mud_client("xterm-256color")
    assert not is_known_mud_client("vt220")


# ---------------------------------------------------------------------------
# MSSP
# ---------------------------------------------------------------------------


def test_encode_mssp_single_values():
    out = encode_mssp({"NAME": "DjangoMOO", "CODEBASE": "DjangoMOO"})
    assert out.startswith(bytes((IAC, SB, OPT_MSSP)))
    assert out.endswith(bytes((IAC, SE)))
    payload = out[3:-2]
    expected = (
        bytes((MSSP_VAR,))
        + b"NAME"
        + bytes((MSSP_VAL,))
        + b"DjangoMOO"
        + bytes((MSSP_VAR,))
        + b"CODEBASE"
        + bytes((MSSP_VAL,))
        + b"DjangoMOO"
    )
    assert payload == expected


def test_encode_mssp_multi_value_repeats_val_tag():
    out = encode_mssp({"LANGUAGE": ["English", "Japanese"]})
    payload = out[3:-2]
    expected = bytes((MSSP_VAR,)) + b"LANGUAGE" + bytes((MSSP_VAL,)) + b"English" + bytes((MSSP_VAL,)) + b"Japanese"
    assert payload == expected


# ---------------------------------------------------------------------------
# CHARSET
# ---------------------------------------------------------------------------


def test_encode_charset_accepted_utf8():
    out = encode_charset_accepted("UTF-8")
    assert out == bytes((IAC, SB, OPT_CHARSET, 2)) + b"UTF-8" + bytes((IAC, SE))


# ---------------------------------------------------------------------------
# MSP
# ---------------------------------------------------------------------------


def test_msp_sound_marker_defaults():
    assert msp_sound_marker("door.wav") == "!!SOUND(door.wav V=100 P=10)"


def test_msp_sound_marker_custom_volume_priority():
    assert msp_sound_marker("bell.wav", volume=50, priority=5) == "!!SOUND(bell.wav V=50 P=5)"


# ---------------------------------------------------------------------------
# IacNegotiator
# ---------------------------------------------------------------------------


def test_negotiator_initial_offers_include_expected_set():
    neg = IacNegotiator()
    offers = neg.initial_offers()
    assert bytes((IAC, WILL, OPT_GMCP)) in offers
    assert bytes((IAC, WILL, OPT_MSSP)) in offers
    assert bytes((IAC, DO, OPT_TTYPE)) in offers
    assert bytes((IAC, DO, OPT_NAWS)) in offers
    # Proactive WONT SGA — Mudlet only enters GA-detect mode after the
    # server explicitly disclaims SGA.
    assert bytes((IAC, WONT, OPT_SGA)) in offers


def test_negotiator_client_do_gmcp_sets_capability():
    neg = IacNegotiator()
    reply = neg.handle(("cmd", DO, OPT_GMCP))
    assert reply == b""  # we already offered WILL
    assert neg.capabilities["gmcp"] is True


def test_negotiator_client_do_unsupported_option_replies_wont():
    neg = IacNegotiator()
    reply = neg.handle(("cmd", DO, OPT_NAWS))  # NAWS is client→server only
    assert reply == encode_cmd(WONT, OPT_NAWS)


def test_negotiator_client_will_ttype_requests_send():
    neg = IacNegotiator()
    reply = neg.handle(("cmd", WILL, OPT_TTYPE))
    # DO TTYPE + IAC SB TTYPE SEND IAC SE
    assert encode_cmd(DO, OPT_TTYPE) in reply
    assert encode_ttype_send() in reply


def test_negotiator_client_will_unsupported_replies_dont():
    neg = IacNegotiator()
    reply = neg.handle(("cmd", WILL, OPT_MSSP))
    assert reply == encode_cmd(DONT, OPT_MSSP)


def test_negotiator_client_dont_disables_capability():
    neg = IacNegotiator()
    neg.handle(("cmd", DO, OPT_GMCP))
    assert neg.capabilities["gmcp"] is True
    neg.handle(("cmd", DONT, OPT_GMCP))
    assert neg.capabilities["gmcp"] is False


def test_negotiator_full_three_stage_mtts():
    captured: list[tuple[str, int]] = []
    neg = IacNegotiator(on_ttype=lambda name, mtts: captured.append((name, mtts)))

    # Client WILL TTYPE → we DO + SEND.
    reply = neg.handle(("cmd", WILL, OPT_TTYPE))
    assert encode_ttype_send() in reply

    # Stage 1: client name. Stage 2: terminal. Stage 3: MTTS bitfield.
    neg.handle(("sb", OPT_TTYPE, bytes((TTYPE_IS,)) + b"Mudlet"))
    assert neg.capabilities["client_name"] == "Mudlet"
    neg.handle(("sb", OPT_TTYPE, bytes((TTYPE_IS,)) + b"XTERM-256COLOR"))
    mtts = MTTS_ANSI | MTTS_UTF8 | MTTS_SCREEN_READER
    neg.handle(("sb", OPT_TTYPE, bytes((TTYPE_IS,)) + f"MTTS {mtts}".encode()))

    assert neg.capabilities["ttype"] is True
    assert neg.capabilities["mtts"] == mtts
    assert captured == [("Mudlet", mtts)]


def test_negotiator_single_stage_ttype_client_finalizes():
    """A client that only offers one TTYPE value should still finalize after one loop."""
    captured: list[tuple[str, int]] = []
    neg = IacNegotiator(on_ttype=lambda n, m: captured.append((n, m)))
    neg.handle(("cmd", WILL, OPT_TTYPE))
    neg.handle(("sb", OPT_TTYPE, bytes((TTYPE_IS,)) + b"VT100"))
    # Second SEND — client repeats the same value.
    neg.handle(("sb", OPT_TTYPE, bytes((TTYPE_IS,)) + b"VT100"))
    assert neg.capabilities["ttype"] is True
    assert neg.capabilities["mtts"] == 0
    assert captured == [("VT100", 0)]


def test_negotiator_gmcp_sb_invokes_callback():
    received: list[tuple[str, object]] = []
    neg = IacNegotiator(on_gmcp=lambda m, d: received.append((m, d)))
    neg.handle(("sb", OPT_GMCP, b'Core.Hello {"client":"Mudlet"}'))
    assert received == [("Core.Hello", {"client": "Mudlet"})]


def test_negotiator_malformed_gmcp_does_not_raise():
    """Malformed GMCP payloads must not crash the session."""
    neg = IacNegotiator(on_gmcp=lambda m, d: None)
    # Not valid JSON after the space.
    neg.handle(("sb", OPT_GMCP, b"Core.Hello {not json}"))


def test_negotiator_client_mssp_request_invokes_provider():
    neg = IacNegotiator(on_mssp_request=lambda: {"NAME": "DjangoMOO"})
    reply = neg.handle(("sb", OPT_MSSP, b""))
    assert reply.startswith(bytes((IAC, SB, OPT_MSSP)))
    assert reply.endswith(bytes((IAC, SE)))


def test_negotiator_charset_request_utf8_accepted():
    neg = IacNegotiator()
    # REQUEST + sep " " + "UTF-8 LATIN-1"
    payload = bytes((1,)) + b" UTF-8 LATIN-1"
    reply = neg.handle(("sb", OPT_CHARSET, payload))
    assert reply == encode_charset_accepted("UTF-8")
    assert neg.capabilities["charset"] is True


def test_negotiator_charset_request_without_utf8_rejected():
    neg = IacNegotiator()
    payload = bytes((1,)) + b" LATIN-1 ASCII"
    reply = neg.handle(("sb", OPT_CHARSET, payload))
    # Rejected frame starts with subcmd 3.
    assert bytes((3,)) in reply
    assert neg.capabilities["charset"] is False
