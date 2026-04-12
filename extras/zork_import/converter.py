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
    ZilTable,
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
# ROUTINE extraction
# ---------------------------------------------------------------------------


def _extract_routine(form: list) -> ZilRoutine:
    """
    Parse a ROUTINE form into a ZilRoutine.

    ZIL header syntax:
        (ROUTINE name (arg1 arg2 "AUX" local1 local2) body-form1 body-form2 ...)
    The arg-list is form[2] if it's a group; body starts at form[2] or form[3].
    """
    name = form[1] if len(form) > 1 else "UNKNOWN"

    params: list[str] = []
    aux_vars: list[str] = []
    body_start = 2

    # form[2] may be a tuple (arg-list group) or immediately a body form
    if len(form) > 2 and isinstance(form[2], tuple):
        arg_list = form[2]
        body_start = 3
        in_aux = False
        for item in arg_list:
            if isinstance(item, str) and item.upper() == "AUX":
                in_aux = True
            elif in_aux:
                # AUX vars may have default values as (VAR default) tuples
                var_name = item[0] if isinstance(item, tuple) else item
                if isinstance(var_name, str):
                    aux_vars.append(var_name.upper())
            else:
                if isinstance(item, str):
                    params.append(item.upper())
                elif isinstance(item, tuple) and item:
                    # (VAR default) form
                    params.append(str(item[0]).upper())

    body = list(form[body_start:])
    raw_zil = repr(form[:6])  # first few elements for inline comment context

    return ZilRoutine(name=name, params=params, aux_vars=aux_vars, body=body, raw_zil=raw_zil)


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------


def _extract_table_values(form: Any) -> list:
    """
    Extract scalar values from a ZIL TABLE or LTABLE form.

    TABLE/LTABLE entries can be strings, integers, or atom references (,NAME).
    We extract only the string and integer values for bootstrap storage.
    """
    if not isinstance(form, list) or not form:
        return []
    head = form[0]
    if head not in ("TABLE", "LTABLE"):
        return []
    values = []
    for item in form[1:]:
        if isinstance(item, str) and not item.isupper():
            # Quoted string value
            values.append(item)
        elif isinstance(item, int):
            values.append(item)
        elif isinstance(item, tuple) and len(item) == 1 and isinstance(item[0], str):
            # Atom reference like ,NAME — store as string atom
            values.append(item[0])
        # Skip nested TABLE, flags, etc.
    return values


def extract_all(
    nodes: list,
) -> tuple[dict[str, ZilRoom], dict[str, ZilObject], dict[str, ZilRoutine], dict[str, ZilTable]]:
    """
    Walk parsed ZIL AST and extract rooms, objects, routines, and tables.

    Returns four dicts keyed by ZIL atom name.
    """
    rooms: dict[str, ZilRoom] = {}
    objects: dict[str, ZilObject] = {}
    routines: dict[str, ZilRoutine] = {}
    tables: dict[str, ZilTable] = {}

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
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                log.warning("Failed to parse ROOM %r: %s", node[1] if len(node) > 1 else "?", exc)

        elif head == "OBJECT" and len(node) >= 2:
            try:
                obj = _extract_object(node)
                objects[obj.atom] = obj
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                log.warning("Failed to parse OBJECT %r: %s", node[1] if len(node) > 1 else "?", exc)

        elif head == "ROUTINE" and len(node) >= 2:
            try:
                routine = _extract_routine(node)
                routines[routine.name] = routine
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                log.warning("Failed to parse ROUTINE %r: %s", node[1] if len(node) > 1 else "?", exc)

        elif head == "GLOBAL" and len(node) >= 3:
            # <GLOBAL NAME <TABLE ...>> or <GLOBAL NAME <LTABLE ...>>
            name = node[1] if isinstance(node[1], str) else None
            value_form = node[2] if len(node) > 2 else None
            if name and isinstance(value_form, list) and value_form and value_form[0] in ("TABLE", "LTABLE"):
                try:
                    values = _extract_table_values(value_form)
                    if values:
                        tables[name] = ZilTable(name=name, values=values)
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    log.warning("Failed to parse GLOBAL TABLE %r: %s", name, exc)

    return rooms, objects, routines, tables
