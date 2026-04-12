"""
Convert parsed ZIL AST nodes into IR dataclasses.
"""

from __future__ import annotations

import logging
from typing import Any

from .ir import (
    DIRECTION_ATOMS,
    ZilExit,
    ZilObject,
    ZilRoom,
    ZilRoutine,
)

log = logging.getLogger(__name__)


def _is_form(node: Any, head: str) -> bool:
    return isinstance(node, list) and len(node) >= 1 and node[0] == head


def _is_group(node: Any) -> bool:
    return isinstance(node, tuple)


def _str_or_none(val: Any) -> str | None:
    return val if isinstance(val, str) else None


# ---------------------------------------------------------------------------
# Exit parsing
# ---------------------------------------------------------------------------


def _parse_exit(direction: str, prop: tuple) -> ZilExit:
    """
    Parse a direction property tuple into a ZilExit.

    Patterns:
        (NORTH TO ROOM-NAME)
        (EAST "blocked message")
        (WEST TO ROOM IF FLAG)
        (WEST TO ROOM IF FLAG ELSE "message")
        (DOWN PER ROUTINE-NAME)
    """
    rest = list(prop[1:])  # everything after the direction atom

    if not rest:
        return ZilExit(
            direction=direction, dest=None, message=None, condition=None, else_message=None, per_routine=None
        )

    # String-only: blocked exit with message
    if isinstance(rest[0], str) and not rest[0].isupper():
        return ZilExit(
            direction=direction, dest=None, message=rest[0], condition=None, else_message=None, per_routine=None
        )
    if isinstance(rest[0], str) and rest[0] == rest[0] and len(rest) == 1 and " " in rest[0]:
        # Multi-word string captured as one string token
        return ZilExit(
            direction=direction, dest=None, message=rest[0], condition=None, else_message=None, per_routine=None
        )

    # PER routine
    if rest[0] == "PER":
        routine = rest[1] if len(rest) > 1 else None
        return ZilExit(
            direction=direction, dest=None, message=None, condition=None, else_message=None, per_routine=routine
        )

    # TO room [IF flag [ELSE "message"]]
    if rest[0] == "TO":
        dest = rest[1] if len(rest) > 1 else None
        condition = None
        else_message = None
        if len(rest) > 2 and rest[2] == "IF":
            condition = rest[3] if len(rest) > 3 else None
            if len(rest) > 4 and rest[4] == "ELSE":
                else_message = rest[5] if len(rest) > 5 else None
        return ZilExit(
            direction=direction,
            dest=dest,
            message=None,
            condition=condition,
            else_message=else_message,
            per_routine=None,
        )

    # Fallback: treat first atom as destination
    if isinstance(rest[0], str):
        return ZilExit(
            direction=direction, dest=rest[0], message=None, condition=None, else_message=None, per_routine=None
        )

    log.warning("Could not parse exit %s: %r", direction, prop)
    return ZilExit(direction=direction, dest=None, message=None, condition=None, else_message=None, per_routine=None)


# ---------------------------------------------------------------------------
# ROOM extraction
# ---------------------------------------------------------------------------


def _extract_room(form: list) -> ZilRoom:
    atom = form[1]
    desc = ""
    ldesc = None
    fdesc = None
    exits: list[ZilExit] = []
    flags: list[str] = []
    globals_list: list[str] = []
    action = None
    value = 0
    pseudo: list[tuple[str, str]] = []

    for prop in form[2:]:
        if not _is_group(prop) or not prop:
            continue
        key = prop[0] if prop else None
        if not isinstance(key, str):
            continue
        key = key.upper()

        if key == "DESC":
            desc = prop[1] if len(prop) > 1 else ""
        elif key == "LDESC":
            ldesc = prop[1] if len(prop) > 1 else None
        elif key == "FDESC":
            fdesc = prop[1] if len(prop) > 1 else None
        elif key in DIRECTION_ATOMS:
            # (IN ROOMS) is the room's container declaration, not an exit direction
            if key == "IN" and len(prop) == 2 and prop[1] == "ROOMS":
                pass
            else:
                exits.append(_parse_exit(key, prop))
        elif key == "FLAGS":
            flags.extend(str(f).upper() for f in prop[1:] if isinstance(f, str))
        elif key == "GLOBAL":
            globals_list.extend(str(g).upper() for g in prop[1:] if isinstance(g, str))
        elif key == "ACTION":
            action = prop[1] if len(prop) > 1 else None
        elif key == "VALUE":
            value = prop[1] if len(prop) > 1 and isinstance(prop[1], int) else 0
        elif key == "PSEUDO":
            # (PSEUDO "word" routine "word2" routine2 ...)
            items = list(prop[1:])
            for i in range(0, len(items) - 1, 2):
                word = items[i] if isinstance(items[i], str) else str(items[i])
                rtn = items[i + 1] if isinstance(items[i + 1], str) else str(items[i + 1])
                pseudo.append((word, rtn))
        elif key in ("IN",):
            pass  # always ROOMS — skip
        else:
            pass  # unknown property — skip silently

    if not desc and ldesc:
        # Some rooms only have LDESC; use first sentence as desc
        desc = ldesc.split(".")[0].strip()

    return ZilRoom(
        atom=atom,
        desc=desc,
        ldesc=ldesc,
        fdesc=fdesc,
        exits=exits,
        flags=flags,
        globals=globals_list,
        action=action,
        value=value,
        pseudo=pseudo,
    )


# ---------------------------------------------------------------------------
# OBJECT extraction
# ---------------------------------------------------------------------------


def _extract_object(form: list) -> ZilObject:
    atom = form[1]
    location = None
    synonyms: list[str] = []
    adjectives: list[str] = []
    desc = None
    ldesc = None
    fdesc = None
    text = None
    flags: list[str] = []
    action = None
    capacity = 0
    size = 5
    value = 0
    tvalue = 0

    for prop in form[2:]:
        if not _is_group(prop) or not prop:
            continue
        key = prop[0] if prop else None
        if not isinstance(key, str):
            continue
        key = key.upper()

        if key == "IN":
            location = prop[1] if len(prop) > 1 else None
        elif key == "SYNONYM":
            synonyms.extend(str(s).lower() for s in prop[1:] if isinstance(s, str))
        elif key == "ADJECTIVE":
            adjectives.extend(str(a).lower() for a in prop[1:] if isinstance(a, str))
        elif key == "DESC":
            desc = prop[1] if len(prop) > 1 else None
        elif key == "LDESC":
            ldesc = prop[1] if len(prop) > 1 else None
        elif key == "FDESC":
            fdesc = prop[1] if len(prop) > 1 else None
        elif key == "TEXT":
            text = prop[1] if len(prop) > 1 else None
        elif key == "FLAGS":
            flags.extend(str(f).upper() for f in prop[1:] if isinstance(f, str))
        elif key == "ACTION":
            action = prop[1] if len(prop) > 1 else None
        elif key == "CAPACITY":
            capacity = prop[1] if len(prop) > 1 and isinstance(prop[1], int) else 0
        elif key == "SIZE":
            size = prop[1] if len(prop) > 1 and isinstance(prop[1], int) else 5
        elif key == "VALUE":
            value = prop[1] if len(prop) > 1 and isinstance(prop[1], int) else 0
        elif key == "TVALUE":
            tvalue = prop[1] if len(prop) > 1 and isinstance(prop[1], int) else 0

    return ZilObject(
        atom=atom,
        location=location,
        synonyms=synonyms,
        adjectives=adjectives,
        desc=desc,
        ldesc=ldesc,
        fdesc=fdesc,
        text=text,
        flags=flags,
        action=action,
        capacity=capacity,
        size=size,
        value=value,
        tvalue=tvalue,
    )


# ---------------------------------------------------------------------------
# ROUTINE extraction (stubs only)
# ---------------------------------------------------------------------------


def _extract_routine(form: list, source_lines: str) -> ZilRoutine:
    name = form[1] if len(form) > 1 else "UNKNOWN"
    # Capture raw body as best-effort repr of the form
    raw = repr(form[:4])  # first few elements for context
    return ZilRoutine(name=name, raw_body=raw)


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------


def extract_all(nodes: list) -> tuple[dict[str, ZilRoom], dict[str, ZilObject], dict[str, ZilRoutine]]:
    """
    Walk parsed ZIL AST and extract rooms, objects, and routines.

    Returns three dicts keyed by ZIL atom name.
    """
    rooms: dict[str, ZilRoom] = {}
    objects: dict[str, ZilObject] = {}
    routines: dict[str, ZilRoutine] = {}

    for node in nodes:
        if not isinstance(node, list) or not node:
            continue
        head = node[0]
        if not isinstance(head, str):
            continue

        if head == "ROOM" and len(node) >= 2:
            try:
                room = _extract_room(node)
                rooms[room.atom] = room
            except Exception as exc:
                log.warning("Failed to parse ROOM %r: %s", node[1] if len(node) > 1 else "?", exc)

        elif head == "OBJECT" and len(node) >= 2:
            try:
                obj = _extract_object(node)
                objects[obj.atom] = obj
            except Exception as exc:
                log.warning("Failed to parse OBJECT %r: %s", node[1] if len(node) > 1 else "?", exc)

        elif head == "ROUTINE" and len(node) >= 2:
            try:
                routine = _extract_routine(node, "")
                routines[routine.name] = routine
            except Exception as exc:
                log.warning("Failed to parse ROUTINE %r: %s", node[1] if len(node) > 1 else "?", exc)

    return rooms, objects, routines
