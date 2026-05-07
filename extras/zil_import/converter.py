"""Convert parsed ZIL AST nodes into IR dataclasses.

See :doc:`/reference/zil-importer`."""

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
    vtype = None

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
        elif key == "VTYPE":
            # ``(VTYPE NONLANDBIT)`` declares the vehicle type atom that
            # ``GOTO`` checks against the destination room's flags.  Stored
            # lower-cased to match the ``ROOM_FLAG_PROPERTIES`` mapping
            # (``NONLANDBIT`` → ``nonlandbit=True`` on water rooms).
            vtype_atom = prop[1] if len(prop) > 1 and isinstance(prop[1], str) else None
            if vtype_atom:
                vtype = vtype_atom.lower()

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
        vtype=vtype,
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
    initial_values: dict = {}
    body_start = 2

    # form[2] may be a tuple (arg-list group) or immediately a body form
    if len(form) > 2 and isinstance(form[2], tuple):
        arg_list = form[2]
        body_start = 3
        in_aux = False
        for item in arg_list:
            # ZIL keyword separators ("AUX", "OPTIONAL") signal the boundary
            # between positional and keyword/optional/aux groups. We treat
            # everything after "AUX" as aux vars and skip the marker itself.
            if isinstance(item, str) and item.upper() in ("AUX", '"AUX"'):
                in_aux = True
                continue
            if isinstance(item, str) and item.upper() in ("OPTIONAL", '"OPTIONAL"'):
                # OPTIONAL marks subsequent params as optional with defaults
                continue
            # AUX vars and optional params may carry initial values as
            # (VAR default) tuples — capture them so the translator can
            # emit a real Python initializer instead of a bare None.
            if isinstance(item, tuple) and item:
                var_name = str(item[0]).upper() if isinstance(item[0], str) else None
                if var_name is None:
                    continue
                if len(item) > 1:
                    initial_values[var_name] = item[1]
                if in_aux:
                    aux_vars.append(var_name)
                else:
                    params.append(var_name)
            elif isinstance(item, str):
                if in_aux:
                    aux_vars.append(item.upper())
                else:
                    params.append(item.upper())

    body = list(form[body_start:])
    raw_zil = repr(form[:6])  # first few elements for inline comment context

    return ZilRoutine(
        name=name,
        params=params,
        aux_vars=aux_vars,
        body=body,
        raw_zil=raw_zil,
        initial_values=initial_values,
    )


# ---------------------------------------------------------------------------
# Top-level extraction
# ---------------------------------------------------------------------------


def _extract_table_values(form: Any) -> list:
    """
    Extract values from a ZIL ``TABLE`` or ``LTABLE`` form.

    Entries can be quoted strings (game text), integers, or bare atom
    references (``RESERVOIR-SOUTH``, etc.).  Bare uppercase atoms are
    *kept* as atom-reference strings — they're how ZIL tables encode
    room/object references.  Parenthesized flag groups like ``(PURE)``
    are discarded.

    For ``LTABLE``, prepend the implicit length so ``LKP`` /
    ``GO-NEXT``'s ``table_get(tbl, 0)`` reads the count.

    The bootstrap output (``015_tables.py``) is responsible for
    resolving atom-reference strings to runtime ``Object`` references
    so that ``lkp`` can compare against ``here()`` etc.
    """
    if not isinstance(form, list) or not form:
        return []
    head = form[0]
    if head not in ("TABLE", "LTABLE"):
        return []
    from .parser import Str

    values = []
    for item in form[1:]:
        if isinstance(item, Str):
            # Quoted string — game text.
            values.append(str(item))
        elif isinstance(item, int):
            values.append(item)
        elif isinstance(item, str):
            # Bare atom — atom reference.  Prefix with ``@`` so the
            # generator can distinguish atom refs from regular strings
            # when emitting bootstrap code.
            values.append("@" + item)
        elif isinstance(item, tuple):
            # Parenthesized flag group like ``(PURE)`` — skip.
            continue
        # Skip nested TABLE/LTABLE (translator emits inner tables
        # separately; we don't currently need nested-table data).
    if head == "LTABLE":
        # ZIL's LTABLE stores the element count at offset 0 implicitly.
        return [len(values)] + values
    return values


def extract_all(
    nodes: list,
) -> tuple[
    dict[str, ZilRoom],
    dict[str, ZilObject],
    dict[str, ZilRoutine],
    dict[str, ZilTable],
    dict[str, object],
    dict[str, list[tuple[int, str]]],
    dict[str, list[str]],
]:
    """
    Walk parsed ZIL AST and extract rooms, objects, routines, tables, globals,
    SYNTAX → V-routine mappings, and SYNONYM aliases.

    Returns seven dicts keyed by ZIL atom name.  ``globals_dict`` maps
    ``<GLOBAL FOO 100>`` → ``{'FOO': 100}`` (scalar globals; table globals go
    into ``tables`` instead).  ``syntax_dict`` maps ``LIGHT → 'V-LAMP-ON'``
    (verb → action V-routine).  ``synonyms_dict`` maps ``ATTACK →
    ['FIGHT', 'HURT', 'INJURE', 'HIT']``.
    """
    rooms: dict[str, ZilRoom] = {}
    objects: dict[str, ZilObject] = {}
    routines: dict[str, ZilRoutine] = {}
    tables: dict[str, ZilTable] = {}
    globals_dict: dict[str, object] = {}
    syntax_dict: dict[str, list[tuple[int, str]]] = {}
    synonyms_dict: dict[str, list[str]] = {}

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
            elif name and isinstance(value_form, (int, str, type(None))):
                # Scalar global: ``<GLOBAL LOAD-ALLOWED 100>`` initialises a
                # zstate slot that ITAKE / V-WALK / etc. read at runtime.
                globals_dict[name] = value_form

        elif head == "SETG" and len(node) >= 3:
            # Top-level ``<SETG ZORK-NUMBER 1>`` initialises a zstate slot the
            # same way ``<GLOBAL FOO 100>`` does — translated routines branch
            # on these via ``player.zstate_get("ZORK-NUMBER")`` and silently
            # fall through to the ZORK-NUMBER == 0 path otherwise.
            name = node[1] if isinstance(node[1], str) else None
            value_form = node[2] if len(node) > 2 else None
            if name and isinstance(value_form, (int, str)) and name not in globals_dict:
                globals_dict[name] = value_form

        elif head == "SYNTAX" and len(node) >= 4:
            # ``<SYNTAX LIGHT OBJECT (FIND LIGHTBIT) ... = V-LAMP-ON>``.
            # Record (object_slots, v_routine) for every rule so the
            # generator can pick the right variant based on whether the
            # player typed an object (``walk`` vs ``walk north``).  Slot
            # constraints are dropped — the V-routine does its own lookup.
            verb = node[1] if isinstance(node[1], str) else None
            if not verb:
                continue
            try:
                eq_idx = next(i for i, t in enumerate(node) if t == "=")
            except StopIteration:
                continue
            object_slots = sum(1 for t in node[2:eq_idx] if t == "OBJECT")
            after_eq = [t for t in node[eq_idx + 1 :] if isinstance(t, str)]
            if not after_eq:
                continue
            v_routine = after_eq[0]
            syntax_dict.setdefault(verb, []).append((object_slots, v_routine))

        elif head == "SYNONYM" and len(node) >= 3:
            # ``<SYNONYM ATTACK FIGHT HURT INJURE HIT>`` — first atom is
            # canonical, the rest are aliases that resolve to the same verb.
            atoms = [t for t in node[1:] if isinstance(t, str)]
            if len(atoms) >= 2:
                synonyms_dict.setdefault(atoms[0], []).extend(atoms[1:])

    return rooms, objects, routines, tables, globals_dict, syntax_dict, synonyms_dict
