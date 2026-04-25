# -*- coding: utf-8 -*-
"""
IAC (telnet subnegotiation) parser, encoder, and per-session negotiator.

DjangoMOO speaks SSH, not telnet. This module is the in-band channel that
MUD-client protocols (GMCP, MSSP, MTTS, MSP, ...) ride on top of. Clients
that connect via `sshelnet <https://gitlab.com/bubblehouse/sshelnet>`_ get
raw 0xFF-prefixed IAC sequences passed through transparently.

Scope: just the IAC framing layer plus the MUD-accessibility protocols
listed in :issue:`16`. We do not implement the wider telnet spec
(NAWS, ECHO, SGA, line-mode, etc.).

Byte plumbing
-------------

asyncssh channels default to UTF-8 encoding in both directions. 0xFF is
invalid UTF-8, so the SSH server reconfigures the channel to ``encoding=None``
(bytes mode) on connect and handles text encoding itself: outbound Rich/
prompt_toolkit strings are UTF-8 encoded in the shell layer before reaching
``_chan.write``, and inbound bytes are decoded after the IAC parser strips
any subnegotiation frames.
"""

from __future__ import annotations

import json
import logging
from typing import Callable

log = logging.getLogger(__name__)

# --- Control bytes ----------------------------------------------------------

IAC = 0xFF
DONT = 0xFE
DO = 0xFD
WONT = 0xFC
WILL = 0xFB
SB = 0xFA
GA = 0xF9
EL = 0xF8
EC = 0xF7
AYT = 0xF6
AO = 0xF5
IP = 0xF4
BRK = 0xF3
DM = 0xF2
NOP = 0xF1
SE = 0xF0
EOR = 0xEF

# --- Options ---------------------------------------------------------------

OPT_BINARY = 0
OPT_ECHO = 1
OPT_SGA = 3
OPT_TTYPE = 24  # RFC 1091 — terminal type; MTTS extends this
OPT_EOR = 25  # RFC 885 — end-of-record
OPT_NAWS = 31  # RFC 1073 — window size (deferred)
OPT_LINEMODE = 34
OPT_CHARSET = 42  # RFC 2066
OPT_MSSP = 70  # Mud Server Status Protocol
OPT_MSP = 90  # Mud Sound Protocol
OPT_MXP = 91  # Mud eXtension Protocol (not implemented)
OPT_GMCP = 201  # Generic MUD Communication Protocol

# TTYPE subnegotiation commands (RFC 1091)
TTYPE_IS = 0
TTYPE_SEND = 1

# CHARSET subnegotiation commands (RFC 2066)
CHARSET_REQUEST = 1
CHARSET_ACCEPTED = 2
CHARSET_REJECTED = 3

# MSSP variable/value separators
MSSP_VAR = 1
MSSP_VAL = 2

# MTTS capability bitfield values (telnet TTYPE third-stage response)
# https://tintin.mudhalla.net/protocols/mtts/
MTTS_ANSI = 1
MTTS_VT100 = 2
MTTS_UTF8 = 4
MTTS_256_COLORS = 8
MTTS_MOUSE_TRACKING = 16
MTTS_OSC_COLOR_PALETTE = 32
MTTS_SCREEN_READER = 64
MTTS_PROXY = 128
MTTS_TRUECOLOR = 256
MTTS_MNES = 512
MTTS_MSLP = 1024

# --- Parser -----------------------------------------------------------------


class IacParser:
    """
    Byte-feed state machine for IAC sequences.

    Feed raw bytes via :meth:`feed`; get back a list of events and the
    residual non-IAC bytes (which should be decoded as UTF-8 by the caller).
    Partial frames across ``feed`` calls are buffered internally.

    Events:

    - ``("cmd", cmd, opt)`` — IAC WILL/WONT/DO/DONT <opt>
    - ``("sb", opt, payload_bytes)`` — IAC SB <opt> <payload> IAC SE
    - ``("ga",)`` — IAC GA
    - ``("eor",)`` — IAC EOR
    """

    _NORMAL = 0
    _IAC = 1
    _IAC_CMD = 2  # saw IAC WILL/WONT/DO/DONT, need opt byte
    _SB_OPT = 3  # saw IAC SB, need opt byte
    _SB_PAYLOAD = 4  # collecting SB payload bytes
    _SB_IAC = 5  # saw IAC inside SB payload

    def __init__(self) -> None:
        self._state = self._NORMAL
        self._pending_cmd: int = 0
        self._sb_opt: int = 0
        self._sb_buf: bytearray = bytearray()

    def feed(self, data: bytes) -> tuple[list[tuple], bytes]:
        """
        Feed raw bytes; return ``(events, residual)``.

        ``residual`` is the portion of ``data`` that was not part of any
        IAC sequence — the caller should decode and forward it to the
        normal input pipeline.
        """
        events: list[tuple] = []
        residual = bytearray()

        for byte in data:
            state = self._state

            if state == self._NORMAL:
                if byte == IAC:
                    self._state = self._IAC
                else:
                    residual.append(byte)

            elif state == self._IAC:
                if byte == IAC:
                    # Escaped 0xFF in the user data stream.
                    residual.append(IAC)
                    self._state = self._NORMAL
                elif byte in (WILL, WONT, DO, DONT):
                    self._pending_cmd = byte
                    self._state = self._IAC_CMD
                elif byte == SB:
                    self._state = self._SB_OPT
                elif byte == GA:
                    events.append(("ga",))
                    self._state = self._NORMAL
                elif byte == EOR:
                    events.append(("eor",))
                    self._state = self._NORMAL
                elif byte in (NOP, DM, BRK, IP, AO, AYT, EC, EL):
                    # Single-byte commands we ignore but must consume.
                    self._state = self._NORMAL
                else:
                    log.debug("unexpected byte after IAC: 0x%02x", byte)
                    self._state = self._NORMAL

            elif state == self._IAC_CMD:
                events.append(("cmd", self._pending_cmd, byte))
                self._pending_cmd = 0
                self._state = self._NORMAL

            elif state == self._SB_OPT:
                self._sb_opt = byte
                self._sb_buf = bytearray()
                self._state = self._SB_PAYLOAD

            elif state == self._SB_PAYLOAD:
                if byte == IAC:
                    self._state = self._SB_IAC
                else:
                    self._sb_buf.append(byte)

            elif state == self._SB_IAC:
                if byte == IAC:
                    # IAC IAC inside SB payload → literal 0xFF byte.
                    self._sb_buf.append(IAC)
                    self._state = self._SB_PAYLOAD
                elif byte == SE:
                    events.append(("sb", self._sb_opt, bytes(self._sb_buf)))
                    self._sb_opt = 0
                    self._sb_buf = bytearray()
                    self._state = self._NORMAL
                else:
                    log.warning(
                        "unexpected byte 0x%02x after IAC in SB payload; aborting frame",
                        byte,
                    )
                    self._sb_opt = 0
                    self._sb_buf = bytearray()
                    self._state = self._NORMAL

        return events, bytes(residual)


# --- Encoders ---------------------------------------------------------------


def encode_cmd(cmd: int, opt: int) -> bytes:
    """Encode IAC WILL/WONT/DO/DONT <opt>."""
    return bytes((IAC, cmd, opt))


def encode_sb(opt: int, payload: bytes) -> bytes:
    """
    Encode IAC SB <opt> <payload> IAC SE, doubling any 0xFF in payload.
    """
    escaped = payload.replace(bytes((IAC,)), bytes((IAC, IAC)))
    return bytes((IAC, SB, opt)) + escaped + bytes((IAC, SE))


def encode_ga() -> bytes:
    return bytes((IAC, GA))


def encode_eor() -> bytes:
    return bytes((IAC, EOR))


# --- GMCP -------------------------------------------------------------------


def encode_gmcp(module: str, data) -> bytes:
    """
    Encode a GMCP frame: ``IAC SB GMCP "<module> <json>" IAC SE``.

    Per the GMCP spec the payload is the module name, a space, and the
    JSON-encoded value. Empty-value messages omit the JSON.
    """
    if data is None:
        payload = module.encode("utf-8")
    else:
        payload = (module + " " + json.dumps(data, separators=(",", ":"))).encode("utf-8")
    return encode_sb(OPT_GMCP, payload)


def parse_gmcp(payload: bytes) -> tuple[str, object]:
    """Inverse of :func:`encode_gmcp` — returns ``(module, data_or_None)``."""
    text = payload.decode("utf-8", errors="replace")
    space = text.find(" ")
    if space == -1:
        return text, None
    module = text[:space]
    raw = text[space + 1 :].strip()
    if not raw:
        return module, None
    return module, json.loads(raw)


# --- TTYPE / MTTS -----------------------------------------------------------


def encode_ttype_send() -> bytes:
    """Encode the server's request for the next TTYPE value."""
    return encode_sb(OPT_TTYPE, bytes((TTYPE_SEND,)))


def parse_ttype_is(payload: bytes) -> str:
    """Parse the client's ``IS <name>`` TTYPE response."""
    if not payload or payload[0] != TTYPE_IS:
        raise ValueError(f"expected TTYPE IS, got {payload!r}")
    return payload[1:].decode("utf-8", errors="replace")


def parse_mtts_bitfield(value: str) -> int:
    """
    Parse a third-stage MTTS response (``MTTS <integer bitfield>``).
    Returns 0 if the value does not match the MTTS format.
    """
    if not value.startswith("MTTS "):
        return 0
    try:
        return int(value[5:])
    except ValueError:
        return 0


def is_known_mud_client(ttype_name: str) -> bool:
    """Heuristic: does this TTYPE name look like a real MUD client?"""
    lowered = ttype_name.lower()
    return any(
        marker in lowered
        for marker in ("mudlet", "mushclient", "tintin", "tinyfugue", "zmud", "cmud", "blowtorch", "mudrammer")
    )


# --- MSSP -------------------------------------------------------------------


def encode_mssp(values: dict[str, str | list[str]]) -> bytes:
    """
    Encode an MSSP response: ``IAC SB MSSP VAR name VAL value ... IAC SE``.

    Multi-valued entries repeat the ``VAL`` tag.
    """
    buf = bytearray()
    for name, value in values.items():
        buf.append(MSSP_VAR)
        buf.extend(name.encode("utf-8"))
        if isinstance(value, list):
            for v in value:
                buf.append(MSSP_VAL)
                buf.extend(str(v).encode("utf-8"))
        else:
            buf.append(MSSP_VAL)
            buf.extend(str(value).encode("utf-8"))
    return encode_sb(OPT_MSSP, bytes(buf))


# --- CHARSET ---------------------------------------------------------------


def encode_charset_request(charsets: list[str], sep: str = " ") -> bytes:
    """Server-initiated CHARSET REQUEST subnegotiation."""
    payload = bytes((CHARSET_REQUEST,)) + sep.encode("ascii")
    payload += sep.encode("ascii").join(c.encode("ascii") for c in charsets)
    return encode_sb(OPT_CHARSET, payload)


def encode_charset_accepted(charset: str) -> bytes:
    """Server reply to a client CHARSET REQUEST."""
    return encode_sb(OPT_CHARSET, bytes((CHARSET_ACCEPTED,)) + charset.encode("ascii"))


def encode_charset_rejected() -> bytes:
    return encode_sb(OPT_CHARSET, bytes((CHARSET_REJECTED,)))


# --- MSP --------------------------------------------------------------------


def msp_sound_marker(name: str, volume: int = 100, priority: int = 10) -> str:
    """
    Return an inline MSP ``!!SOUND(...)`` marker.

    Emitted as part of the text stream when MSP is negotiated; clients that
    have not negotiated MSP will render it literally, which is why the SDK
    gates this behind the negotiated capability.
    """
    return f"!!SOUND({name} V={volume} P={priority})"


def msp_music_marker(name: str, volume: int = 100) -> str:
    return f"!!MUSIC({name} V={volume})"


# --- Negotiator -------------------------------------------------------------


class IacNegotiator:
    """
    Per-session capability state and outbound command queue.

    The SSH server instantiates one of these per connection. It feeds
    parsed IAC events in via :meth:`handle`, which returns a list of bytes
    objects to send back on the channel (responses, subnegotiation
    requests).

    Capability flags are exposed on ``self.capabilities`` for the shell
    layer to mirror into ``_session_settings[...]["iac"]`` so verbs in
    Celery can branch on them.
    """

    # Options we're willing to enable on our side (WILL). SGA is intentionally
    # absent — agreeing to "suppress go-ahead" would tell MUD clients to stop
    # expecting an IAC GA after each prompt, which breaks Mudlet's mapper
    # auto-detection.
    _WE_OFFER = frozenset({OPT_GMCP, OPT_MSSP, OPT_MSP, OPT_EOR, OPT_CHARSET})

    # Options we want the client to enable on its side (DO).
    _WE_ACCEPT_CLIENT = frozenset({OPT_TTYPE, OPT_NAWS, OPT_CHARSET})

    def __init__(
        self,
        on_ttype: Callable[[str, int], None] | None = None,
        on_gmcp: Callable[[str, object], None] | None = None,
        on_mssp_request: Callable[[], dict[str, str | list[str]]] | None = None,
    ) -> None:
        self.capabilities: dict[str, object] = {
            "gmcp": False,
            "mssp": False,
            "msp": False,
            "eor": False,
            "charset": False,
            "ttype": False,
            "mtts": 0,
            "client_name": "",
            "client_version": "",
        }
        self._ttype_stage = 0  # 0=none, 1=name, 2=term, 3=mtts
        self._ttype_last = ""
        self._on_ttype = on_ttype
        self._on_gmcp = on_gmcp
        self._on_mssp_request = on_mssp_request

    def initial_offers(self) -> bytes:
        """
        Return the initial set of IAC commands to send on session start.

        Includes a proactive ``WONT SGA``: Mudlet (and many MUD clients) only
        enter "expect IAC GA after each prompt" mode after the server has
        explicitly disclaimed SGA. Without it the GA bytes we emit get
        ignored and the mapper auto-detect / prompt-line heuristic stays in
        the ``<no GA>`` state.
        """
        return b"".join(
            [
                encode_cmd(WILL, OPT_GMCP),
                encode_cmd(WILL, OPT_MSSP),
                encode_cmd(WILL, OPT_MSP),
                encode_cmd(WILL, OPT_EOR),
                encode_cmd(WILL, OPT_CHARSET),
                encode_cmd(WONT, OPT_SGA),
                encode_cmd(DO, OPT_TTYPE),
                encode_cmd(DO, OPT_NAWS),
            ]
        )

    def handle(self, event: tuple) -> bytes:
        """Dispatch a parsed IAC event; return reply bytes (possibly empty)."""
        kind = event[0]
        if kind == "cmd":
            return self._handle_cmd(event[1], event[2])
        if kind == "sb":
            return self._handle_sb(event[1], event[2])
        return b""

    def _handle_cmd(self, cmd: int, opt: int) -> bytes:
        if cmd == DO:
            if opt in self._WE_OFFER:
                self._mark_enabled(opt)
                # We already offered with WILL; DO confirms — no reply needed.
                # But if the client DOes before we offered, reply WILL.
                return b""
            return encode_cmd(WONT, opt)
        if cmd == DONT:
            self._mark_disabled(opt)
            return encode_cmd(WONT, opt) if opt in self._WE_OFFER else b""
        if cmd == WILL:
            if opt in self._WE_ACCEPT_CLIENT:
                if opt == OPT_TTYPE:
                    self._ttype_stage = 1
                    return encode_cmd(DO, opt) + encode_ttype_send()
                return encode_cmd(DO, opt)
            return encode_cmd(DONT, opt)
        if cmd == WONT:
            return encode_cmd(DONT, opt)
        return b""

    def _handle_sb(self, opt: int, payload: bytes) -> bytes:
        if opt == OPT_TTYPE:
            return self._handle_ttype_sb(payload)
        if opt == OPT_GMCP:
            if self._on_gmcp is not None:
                try:
                    module, data = parse_gmcp(payload)
                    self._on_gmcp(module, data)
                except (ValueError, json.JSONDecodeError):
                    log.warning("malformed GMCP payload: %r", payload)
            return b""
        if opt == OPT_MSSP:
            # Client-initiated MSSP request; respond with server info.
            if self._on_mssp_request is not None:
                return encode_mssp(self._on_mssp_request())
            return b""
        if opt == OPT_CHARSET:
            return self._handle_charset_sb(payload)
        return b""

    def _handle_ttype_sb(self, payload: bytes) -> bytes:
        try:
            value = parse_ttype_is(payload)
        except ValueError:
            return b""

        stage = self._ttype_stage
        if stage == 1:
            self.capabilities["client_name"] = value
            self._ttype_last = value
            self._ttype_stage = 2
            return encode_ttype_send()
        if stage == 2:
            # Second-stage response is the preferred terminal type (e.g. XTERM-256COLOR).
            self.capabilities["terminal"] = value
            if value == self._ttype_last:
                # Client has only one TTYPE to offer; no third stage.
                self._finalize_ttype()
                return b""
            self._ttype_last = value
            self._ttype_stage = 3
            return encode_ttype_send()
        if stage == 3:
            mtts = parse_mtts_bitfield(value)
            if mtts:
                self.capabilities["mtts"] = mtts
            elif value == self._ttype_last:
                # Client looped — no MTTS, we're done.
                pass
            else:
                # Unexpected third stage; record anyway.
                self.capabilities["terminal_extra"] = value
            self._finalize_ttype()
            return b""
        return b""

    def _finalize_ttype(self) -> None:
        self.capabilities["ttype"] = True
        if self._on_ttype is not None:
            self._on_ttype(str(self.capabilities.get("client_name", "")), int(self.capabilities.get("mtts", 0) or 0))
        self._ttype_stage = 0

    def _handle_charset_sb(self, payload: bytes) -> bytes:
        if not payload:
            return b""
        subcmd = payload[0]
        if subcmd != CHARSET_REQUEST:
            return b""
        rest = payload[1:]
        if not rest:
            return encode_charset_rejected()
        sep = rest[:1]
        choices = rest[1:].split(sep)
        for choice in choices:
            name = choice.decode("ascii", errors="ignore").strip().upper()
            if name in ("UTF-8", "UTF8"):
                self.capabilities["charset"] = True
                return encode_charset_accepted("UTF-8")
        return encode_charset_rejected()

    def _mark_enabled(self, opt: int) -> None:
        label = self._opt_label(opt)
        if label:
            self.capabilities[label] = True

    def _mark_disabled(self, opt: int) -> None:
        label = self._opt_label(opt)
        if label:
            self.capabilities[label] = False

    @staticmethod
    def _opt_label(opt: int) -> str:
        return {
            OPT_GMCP: "gmcp",
            OPT_MSSP: "mssp",
            OPT_MSP: "msp",
            OPT_EOR: "eor",
            OPT_CHARSET: "charset",
        }.get(opt, "")
