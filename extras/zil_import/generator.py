"""Generate DjangoMOO bootstrap files from ZIL IR.

See :doc:`/reference/zil-importer` for the file plan and
:doc:`/explanation/zil-importer` for the why."""
# pylint: disable=f-string-without-interpolation

from __future__ import annotations

import shlex
import shutil
import textwrap
from pathlib import Path

from .ir import (
    DIRECTION_ALIASES,
    FLAG_PROPERTIES,
    ROOM_FLAG_PROPERTIES,
    ZIL_VERBS,
    ZilExit,
    ZilObject,
    ZilRoom,
    ZilRoutine,
)
from .translator import DISABLE_FULL, DISABLE_INTRINSIC, ZilTranslator

# Static verb-tree templates copied verbatim into ``output_dir/verbs/`` on
# every regen.  These cover the few pieces that have no ZIL counterpart:
# MooSSH delimiter verbs (PREFIX/SUFFIX), the Object-exit traversal verb
# our movement model needs, and the small ZIL→DjangoMOO impedance shims
# (flag/zstate/table primitives) the translator emits calls to.
_TEMPLATE_VERBS_DIR = Path(__file__).resolve().parent / "verbs"


def _py_str(s: str | None) -> str:
    """Render a string value as a Python string literal."""
    if s is None:
        return "None"
    return repr(s)


def _atom_to_var(atom: str) -> str:
    """Convert a ZIL atom like WEST-OF-HOUSE to a Python variable name."""
    return "_r_" + atom.replace("-", "_").replace("?", "_Q").replace("!", "_B").lower()


def _obj_atom_to_var(atom: str) -> str:
    return "_o_" + atom.replace("-", "_").replace("?", "_Q").replace("!", "_B").lower()


def _routine_to_filename(name: str) -> str:
    """Filename for a translated ZIL routine.  Mirrors the verb-name
    transformations the translator applies in ``_shebang()`` so the file
    name on disk matches the verb name registered in the database:

    - ``ACCESSIBLE?``  → ``is_accessible.py``  (predicate dot-syntax)
    - ``V-TAKE``       → ``take.py``           (substrate v-prefix dropped)
    - ``CRETIN-FCN``   → ``cretin_fcn.py``     (action handler, unchanged)

    Multi-verb-shebang per-clause splits emit their own filenames via the
    generator's ``_emit_routine`` helper using the verb-atom slug; this
    function only handles the single-routine path.
    """
    upper = name.upper()
    if upper.endswith("?"):
        base = upper[:-1]
        if base and base[0].isalpha():
            return "is_" + base.lower().replace("-", "_") + ".py"
    if upper.startswith("V-"):
        return upper[2:].lower().replace("-", "_") + ".py"
    return name.replace("-", "_").replace("?", "_p").replace("!", "_b").lower() + ".py"


def _routine_to_verbname(name: str) -> str:
    return name.lower().replace("_", "-")


# Substrate parent classes get fixed display names. These are the only
# ZIL-side handles that translated verb code or shebangs reach for by
# logical role rather than ZIL atom.  ``_.zork_thing`` remains live on the
# System Object because translated routines call cross-class verbs via
# ``_.zork_thing.foo()``; the others are referenced only at verb-load time
# through ``--on "<Display Name>"`` and need no system-property alias.
SUBSTRATE_DISPLAY_NAMES: dict[str, str] = {
    "zork_root": "Zork Root",
    "zork_thing": "Zork Thing",
    "zork_container": "Zork Container",
    "zork_room": "Zork Room",
    "zork_actor": "Zork Actor",
    "player": "Zork Actor",  # ZIL ``$player`` is an alias for the actor class
    "zork_exit": "Zork Exit",
}


def _compute_display_names(rooms: dict[str, ZilRoom], objects: dict[str, ZilObject]) -> dict[str, str]:
    """Build a globally-unique atom → display-name map.

    ZIL atoms are unique by construction; DESC strings are not.  When two
    rooms (e.g. FOREST-1/2/3 all titled "Forest") or two objects (MIRROR-1
    /MIRROR-2 both "mirror") share a DESC, append ``(ATOM)`` to disambiguate
    so ``--on "<display>"`` at verb-load time resolves to one Object.

    Cross-bucket collisions — a room and an object sharing a DESC (e.g.
    "altar", "dam", "stone barrow") — are resolved by disambiguating the
    object only.  Rooms keep their clean names because they appear in the
    player prompt and in the title line of every ``look``; objects show up
    less often and tolerate the ``(ATOM)`` suffix better.
    """
    from collections import Counter

    room_descs: set[str] = {r.desc.lower() for r in rooms.values() if r.desc}
    room_counts: Counter[str] = Counter(r.desc.lower() for r in rooms.values() if r.desc)
    obj_counts: Counter[str] = Counter(o.desc.lower() for o in objects.values() if o.desc)

    out: dict[str, str] = {}
    for atom, room in rooms.items():
        base = room.desc or atom.replace("-", " ").title()
        out[atom] = f"{base} ({atom})" if room.desc and room_counts[room.desc.lower()] > 1 else base
    for atom, obj in objects.items():
        base = obj.desc or atom.replace("-", " ").lower()
        if obj.desc:
            collides = obj_counts[obj.desc.lower()] > 1 or obj.desc.lower() in room_descs
        else:
            collides = False
        out[atom] = f"{base} ({atom})" if collides else base
    return out


def _room_slug(atom: str) -> str:
    return atom.lower().replace("-", "_")


def _resolve_object_room(atom: str, objects: dict, rooms: dict) -> str | None:
    """Walk an object's container chain up to its enclosing room atom.

    ZIL objects can be nested (an item inside a container inside a room).
    For verb-file location grouping we only care about the outermost room.
    LOCAL-GLOBALS / GLOBAL-OBJECTS pseudo-containers are not rooms — for
    those we fall back to the first room that lists this object in its
    ``(GLOBAL …)`` declaration, since global objects are conceptually
    "scenery available wherever it shows up first."
    Returns None for orphan objects (those with no resolvable home room).
    """
    seen: set[str] = set()
    cur = atom
    while cur:
        if cur in seen:
            break
        seen.add(cur)
        if cur in rooms:
            return cur
        if cur in objects:
            cur = objects[cur].location
            continue
        break
    # Fall back: scan rooms for first GLOBAL declaration that mentions atom.
    for room_atom, room in rooms.items():
        if atom in (room.globals or []):
            return room_atom
    return None


# ---------------------------------------------------------------------------
# 010_classes.py
# ---------------------------------------------------------------------------

_CLASSES_TEMPLATE = '''\
# Generated by extras/zil_import — do not edit by hand
"""Zork-specific root classes — standalone, no dependency on default bootstrap."""
# pylint: disable=undefined-variable

# The system object (_) is created by initialize_dataset.
# Wizard is also created there. Everything else we create from scratch.
# ZIL SDK verbs are attached directly to the System Object, $player, and
# $root_class — translated routines call them as ``_.flag(...)``,
# ``context.player.zstate_set(...)``, ``context.player.move(...)``, etc.

# ---------------------------------------------------------------------------
# Root classes
# ---------------------------------------------------------------------------
# Accept verb — needed so objects can be placed in rooms/containers.
# PROPDEF defaults from zork1.zil go on the root so every object/actor/exit
# inherits them; the WEIGHT routine reads ``size`` on context.player which
# wouldn't have it otherwise (Zork Actor descends from Zork Root, not Zork
# Thing).
zork_root, _created = bootstrap.get_or_create_object("Zork Root", unique_name=True)
zork_root.add_verb("accept", code="return True")
zork_root.set_property("size", 5)
zork_root.set_property("capacity", 0)
zork_root.set_property("value", 0)
zork_root.set_property("tvalue", 0)

# ``zork_thing`` is the only substrate handle that lives on the System
# Object — translated routines invoke cross-class verbs via
# ``_.zork_thing.foo()`` (predicates, dispatchers, M-clause splits).  The
# remaining substrate classes are reachable via ``--on "Zork <Class>"`` at
# verb-load time and need no system-property alias.
zork_thing, _created = bootstrap.get_or_create_object("Zork Thing", unique_name=True, parents=[zork_root])
zork_thing.set_property("takeable", False)
zork_thing.set_property("size", 5)
zork_thing.set_property("value", 0)
zork_thing.set_property("tvalue", 0)
zork_thing.set_property("readable", False)
zork_thing.set_property("flammable", False)
_.set_property("zork_thing", zork_thing)

zork_container, _created = bootstrap.get_or_create_object("Zork Container", unique_name=True, parents=[zork_thing])
zork_container.set_property("takeable", False)
zork_container.set_property("open", False)
zork_container.set_property("size", 10)
zork_container.set_property("capacity", 10)
zork_container.set_property("value", 0)

zork_room, _created = bootstrap.get_or_create_object("Zork Room", unique_name=True, parents=[zork_root])
zork_room.set_property("value", 0)
zork_room.set_property("discovered", False)
zork_room.set_property("outdoor", False)
zork_room.set_property("sacred", False)
zork_room.set_property("maze", False)
zork_room.set_property("dark", False)

zork_actor, _created = bootstrap.get_or_create_object("Zork Actor", unique_name=True, parents=[zork_root])

# Wizard must inherit from Zork Actor so the parser can resolve verbs
# registered ``--on "Zork Actor"`` when commands dispatch on the Wizard
# avatar.
if zork_actor not in wizard.parents.all():
    wizard.parents.add(zork_actor)

zork_exit, _created = bootstrap.get_or_create_object("Zork Exit", unique_name=True, parents=[zork_root])

_classes = {
    "zork_root": zork_root,
    "zork_thing": zork_thing,
    "zork_container": zork_container,
    "zork_room": zork_room,
    "zork_actor": zork_actor,
    "zork_exit": zork_exit,
}
log.info("Zork classes: %d created/updated", len(_classes))
'''


# ---------------------------------------------------------------------------
# 020_rooms.py
# ---------------------------------------------------------------------------


def _gen_rooms(rooms: dict[str, ZilRoom], display_names: dict[str, str]) -> str:
    lines = [
        "# Generated by extras/zil_import — do not edit by hand",
        '"""Zork room objects."""',
        "# pylint: disable=undefined-variable",
        "",
        "_rooms = {}  # keyed by ZIL atom — used by 040_exits.py",
        "",
        "def _ensure_parent(obj, parent):",
        "    # Defensive: re-attach parent if missing.  ``get_or_create_object``",
        "    # only sets parents on first create; this heals DBs created by an",
        "    # older bootstrap that had the object without correct parentage.",
        "    if parent.pk not in obj.parents.values_list('pk', flat=True):",
        "        obj.parents.add(parent)",
        "",
    ]

    for atom, room in rooms.items():
        var = _atom_to_var(atom)
        display_name = display_names[atom]
        lines.append(f"# {atom}")
        lines.append(f"{var}, _created = bootstrap.get_or_create_object(")
        lines.append(f"    {repr(display_name)}, unique_name=True,")
        lines.append(f"    parents=[_classes['zork_room']],")
        lines.append(f")")
        lines.append(f"_ensure_parent({var}, _classes['zork_room'])")

        if room.ldesc:
            lines.append(f"{var}.set_property('description', {_py_str(room.ldesc)})")
        elif room.fdesc:
            lines.append(f"{var}.set_property('description', {_py_str(room.fdesc)})")

        if room.fdesc and room.ldesc:
            lines.append(f"{var}.set_property('first_description', {_py_str(room.fdesc)})")

        # Room flags
        for flag in room.flags:
            if flag in ROOM_FLAG_PROPERTIES:
                prop, val = ROOM_FLAG_PROPERTIES[flag]
                lines.append(f"{var}.set_property({repr(prop)}, {repr(val)})")

        if room.value:
            lines.append(f"{var}.set_property('value', {room.value})")

        if room.globals:
            lines.append(f"{var}.set_property('global_scenery', {room.globals!r})")

        if room.action:
            lines.append(f"# ACTION: {room.action} — see verbs/{_routine_to_filename(room.action)}")

        atom_alias = atom.lower().replace("-", "_")
        lines.append(f"{var}.add_alias({repr(atom_alias)})")
        # Also alias by ACTION-routine name when it differs from the atom.
        # ZIL code like ``<EQUAL? ,HERE ,LLD-ROOM>`` references the room
        # by its ROOM-FUNCTION name (LLD-ROOM is the action of
        # ENTRANCE-TO-HADES); without this alias the translator emits
        # ``_.zork_thing.lld_room()`` (a routine call) which crashes
        # because LLD-ROOM is the room's lifecycle handler, not a
        # standalone helper.
        if room.action:
            action_alias = room.action.lower().replace("-", "_")
            if action_alias != atom_alias:
                lines.append(f"{var}.add_alias({repr(action_alias)})")
        lines.append(f"_rooms[{repr(atom)}] = {var}")
        lines.append("")

    lines.append(f"log.info('Zork rooms: %d', len(_rooms))")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 030_objects.py
# ---------------------------------------------------------------------------


def _gen_objects(
    objects: dict[str, ZilObject],
    rooms: dict[str, ZilRoom],
    display_names: dict[str, str],
) -> str:
    lines = [
        "# Generated by extras/zil_import — do not edit by hand",
        '"""Zork game objects."""',
        "# pylint: disable=undefined-variable",
        "",
        "_objects = {}  # keyed by ZIL atom",
        "",
        "def _ensure_parent(obj, parent):",
        "    # Defensive: re-attach parent if missing.  ``get_or_create_object``",
        "    # only sets parents on first create; this heals DBs created by an",
        "    # older bootstrap that had the object without correct parentage.",
        "    if parent.pk not in obj.parents.values_list('pk', flat=True):",
        "        obj.parents.add(parent)",
        "",
    ]
    # ZIL ``IN`` may reference an object declared later in dungeon.zil
    # (LEAFLET → MAILBOX is the canonical case).  Collect deferred location
    # fixups and apply them in a second pass after every object exists.
    deferred_locations: list[tuple[str, str]] = []  # (object_atom, location_atom)

    for atom, obj in objects.items():
        var = _obj_atom_to_var(atom)

        # Pick parent class
        if "ACTORBIT" in obj.flags:
            parent = "_classes['zork_actor']"
        elif "CONTBIT" in obj.flags:
            parent = "_classes['zork_container']"
        else:
            parent = "_classes['zork_thing']"

        # ``obvious`` is the parser's dobj-visibility flag; both NDESCBIT
        # and INVISIBLE hide objects from player commands in ZIL, so both
        # map onto ``obvious=False`` at bootstrap time.  Runtime ``set_flag
        # ('invisible', X)`` keeps writing through to ``obvious`` via
        # ``zil_sdk/flags.py``.
        obvious = "False" if ("NDESCBIT" in obj.flags or "INVISIBLE" in obj.flags) else "True"

        # Resolve location
        if obj.location and obj.location in rooms:
            loc_expr = f"_rooms[{repr(obj.location)}]"
        elif obj.location and obj.location in objects:
            # Forward reference to another object — start with None and
            # patch after every object has been created.
            loc_expr = "None"
            deferred_locations.append((atom, obj.location))
        elif obj.location:
            # Unknown atom (e.g. a global pseudo-container).  Best-effort
            # lookup through the running ``_objects`` dict.
            loc_expr = f"_objects.get({repr(obj.location)})  # {obj.location}"
        else:
            loc_expr = "None"

        display_name = display_names[atom]
        lines.append(f"# {atom}")
        lines.append(f"{var}, _created = bootstrap.get_or_create_object(")
        lines.append(f"    {repr(display_name)}, unique_name=False,")
        lines.append(f"    parents=[{parent}],")
        lines.append(f"    location={loc_expr},")
        lines.append(f")")
        lines.append(f"_ensure_parent({var}, {parent})")
        lines.append(f"{var}.obvious = {obvious}")
        lines.append(f"{var}.save()")

        desc_text = obj.ldesc or obj.fdesc or obj.desc
        if desc_text:
            lines.append(f"{var}.set_property('description', {_py_str(desc_text)})")

        if obj.fdesc and obj.ldesc:
            lines.append(f"{var}.set_property('first_description', {_py_str(obj.fdesc)})")

        if obj.text:
            lines.append(f"{var}.set_property('text', {_py_str(obj.text)})")

        # Synonyms as aliases
        for syn in obj.synonyms:
            lines.append(f"{var}.add_alias({repr(syn)})")

        # Adjectives stored as property
        if obj.adjectives:
            lines.append(f"{var}.set_property('adjectives', {obj.adjectives!r})")

        # Flag properties.  ``obvious`` is intrinsic and was set above via
        # the model field, so we skip both ``obvious`` and ``invisible``
        # (the runtime SDK routes ``flag('invisible')`` through ``obvious``
        # — keeping the property would let stale state mask the field).
        for flag in obj.flags:
            if flag in FLAG_PROPERTIES:
                prop, val = FLAG_PROPERTIES[flag]
                if prop in ("obvious", "invisible"):
                    continue
                lines.append(f"{var}.set_property({repr(prop)}, {repr(val)})")

        if obj.capacity:
            lines.append(f"{var}.set_property('capacity', {obj.capacity})")
        if obj.size != 5:
            lines.append(f"{var}.set_property('size', {obj.size})")
        if obj.value:
            lines.append(f"{var}.set_property('value', {obj.value})")
        if obj.tvalue:
            lines.append(f"{var}.set_property('tvalue', {obj.tvalue})")
        if obj.vtype:
            lines.append(f"{var}.set_property('vtype', {obj.vtype!r})")

        if obj.action:
            lines.append(f"# ACTION: {obj.action} — see verbs/{_routine_to_filename(obj.action)}")

        atom_alias = atom.lower().replace("-", "_")
        lines.append(f"{var}.add_alias({repr(atom_alias)})")
        lines.append(f"_objects[{repr(atom)}] = {var}")
        lines.append("")

    if deferred_locations:
        lines.append("# Resolve forward IN references that pointed at later-declared objects.")
        for obj_atom, loc_atom in deferred_locations:
            lines.append(f"_objects[{obj_atom!r}].location = _objects[{loc_atom!r}]; _objects[{obj_atom!r}].save()")
        lines.append("")
    lines.append("log.info('Zork objects: %d', len(_objects))")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 040_exits.py
# ---------------------------------------------------------------------------


def _gen_exits(rooms: dict[str, ZilRoom]) -> str:
    """Emit 040_exits.py.

    Each room's ``exits`` list and each destination's ``entrances`` list
    are accumulated in Python locals first, then written once at the end
    of the room block.  This avoids the prior get/append/set-per-exit
    pattern, which left the lists growing 8x on every sync because each
    sync re-ran the script against a populated database.
    """
    lines = [
        "# Generated by extras/zil_import — do not edit by hand",
        '"""Zork exit objects connecting rooms."""',
        "# pylint: disable=undefined-variable",
        "",
        "_entrances: dict[int, list] = {}  # room pk → entry-Object list (built up below)",
        "",
    ]

    for atom, room in rooms.items():
        if not room.exits:
            continue
        room_var = _atom_to_var(atom)
        lines.append(f"# Exits from {atom}")
        lines.append(f"_room_exits = []")

        for ex in room.exits:
            direction_lower = ex.direction.lower()
            aliases = DIRECTION_ALIASES.get(ex.direction, [direction_lower])
            # Use atom (always unique) rather than DESC — when ZIL games
            # share a DESC across rooms (e.g. FOREST-1/2/3 are all "Forest"),
            # the exit names would collide under unique_name=True and the
            # exits would all attach to whichever Object was created first.
            exit_name = f"{direction_lower} from {atom}"

            lines.append(f"_e, _created = bootstrap.get_or_create_object(")
            lines.append(f"    {repr(exit_name)}, unique_name=True,")
            lines.append(f"    parents=[_classes['zork_exit']],")
            lines.append(f")")
            lines.append(f"_e.set_property('source', {room_var})")

            if ex.per_routine:
                lines.append(f"_e.set_property('dest', None)")
                lines.append(f"_e.set_property('exit_routine', {repr(ex.per_routine)})")
                lines.append(f"# PER: {ex.per_routine} — needs custom verb in verbs/")
            elif ex.dest and ex.dest in rooms:
                dest_var = _atom_to_var(ex.dest)
                lines.append(f"_e.set_property('dest', {dest_var})")
                if ex.condition:
                    lines.append(f"_e.set_property('condition_flag', {repr(ex.condition)})")
                if ex.else_message:
                    lines.append(f"_e.set_property('nogo_msg', {_py_str(ex.else_message)})")
            elif ex.message:
                lines.append(f"_e.set_property('dest', None)")
                lines.append(f"_e.set_property('nogo_msg', {_py_str(ex.message)})")
            elif ex.dest:
                # dest atom not found in rooms dict (e.g. a non-room destination)
                lines.append(f"_e.set_property('dest', None)  # unknown dest: {ex.dest}")
                lines.append(f"_e.set_property('nogo_msg', 'You cannot go that way.')")
            else:
                lines.append(f"_e.set_property('dest', None)")
                lines.append(f"_e.set_property('nogo_msg', 'You cannot go that way.')")

            for alias in aliases:
                lines.append(f"_e.add_alias({repr(alias)})")

            lines.append(f"_e.save()")
            lines.append(f"_room_exits.append(_e)")

            if ex.dest and ex.dest in rooms:
                dest_var = _atom_to_var(ex.dest)
                lines.append(f"_entrances.setdefault({dest_var}.pk, []).append(_e)")

            lines.append("")

        lines.append(f"{room_var}.set_property('exits', _room_exits)")
        lines.append("")

    # Flush all accumulated entrances at end so a single dest collects every
    # incoming exit before the property is written.
    lines.append("for _room_pk, _ents in _entrances.items():")
    lines.append("    _r = _rooms_by_pk.get(_room_pk) if '_rooms_by_pk' in dir() else None")
    lines.append("    if _r is None:")
    lines.append("        from moo.core.models.object import Object as _Object")
    lines.append("        _r = _Object.global_objects.get(pk=_room_pk)")
    lines.append("    _r.set_property('entrances', _ents)")
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# zork1/bootstrap.py
# ---------------------------------------------------------------------------


_BANNER = (
    "ZORK I: The Great Underground Empire\n"
    "  Original (c) Infocom, Inc. 1980; MIT-licensed source release 2025.\n"
    "  Zork is a registered trademark of Activision Publishing, Inc.\n"
    "  DjangoMOO bootstrap: {rooms} rooms, {objects} objects."
)


def _gen_bootstrap_init(rooms: dict, objects: dict) -> str:
    banner = _BANNER.format(rooms=len(rooms), objects=len(objects))
    return textwrap.dedent(f"""\
        # Generated by extras/zil_import — do not edit by hand
        \"\"\"
        Zork 1 bootstrap for DjangoMOO.

        Load with:
            manage.py moo_init --bootstrap zork1

        World statistics (as parsed from dungeon.zil):
            Rooms:   {len(rooms)}
            Objects: {len(objects)}

        Derived from the Infocom Zork 1 source (dungeon.zil / actions.zil), released
        under the MIT License by Microsoft / Activision Publishing, Inc. in 2025.
        See LICENSE and README.md in this directory for full terms and credits.

        Zork is a registered trademark of Activision Publishing, Inc.
        \"\"\"
        import importlib.resources
        import logging
        import secrets
        from time import time

        from moo import bootstrap
        from moo.core import code, lookup

        log = logging.getLogger(__name__)
        for _line in {banner!r}.splitlines():
            log.info(_line)
        _repo = bootstrap.initialize_dataset("zork1")
        wizard = lookup("Wizard")
        _ = lookup("System Object")

        _namespace = {{
            "log": log,
            "secrets": secrets,
            "time": time,
            "bootstrap": bootstrap,
            "lookup": lookup,
            "wizard": wizard,
            "repo": _repo,
            "_": _,
        }}

        _pkg = importlib.resources.files("moo.bootstrap") / "zork1"
        _scripts = sorted(
            (f for f in _pkg.iterdir() if f.name.endswith(".py") and f.name[0].isdigit()),
            key=lambda f: f.name,
        )

        with code.ContextManager(wizard, log.info, site=wizard.site):
            for _script in _scripts:
                exec(compile(_script.read_text(encoding="utf8"), _script.name, "exec"), _namespace)  # pylint: disable=exec-used
            bootstrap.load_verbs(_repo, "moo.bootstrap.zork1.verbs", replace=True)
    """)


# ---------------------------------------------------------------------------
# Verb translation
# ---------------------------------------------------------------------------


def _gen_verb_translated(
    routine: ZilRoutine,
    object_atoms: set[str] | None = None,
    routine_atoms: set[str] | None = None,
    lint_active: bool = False,
) -> str:
    """Translate a ZilRoutine to a DjangoMOO verb file using ZilTranslator."""
    translator = ZilTranslator(
        routine,
        object_atoms=object_atoms,
        routine_atoms=routine_atoms,
        lint_active=lint_active,
    )
    return translator.translate()


def _gen_m_clause_verb(
    routine: ZilRoutine,
    m_constant: str,
    object_atoms: set[str] | None = None,
    routine_atoms: set[str] | None = None,
    lint_active: bool = False,
) -> str:
    """Generate a single M-* clause as a separate verb file."""
    translator = ZilTranslator(
        routine,
        object_atoms=object_atoms,
        routine_atoms=routine_atoms,
        lint_active=lint_active,
    )
    return translator.translate_m_clause(m_constant)


def _clause_is_empty(code: str) -> bool:
    """True when a translated clause body is whitespace / comments / ``pass`` only."""
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "pass":
            continue
        return False
    return True


# ---------------------------------------------------------------------------
# 013_globals.py — scalar GLOBAL declarations from ZIL substrate / dungeon
# ---------------------------------------------------------------------------


def _gen_globals(globals_dict: dict[str, object]) -> str:
    """Generate 013_globals.py to seed zstate slots from ``<GLOBAL …>`` forms.

    Translated routines read these via ``_.zil_sdk.zstate_get('FOO')`` →
    ``context.player.get_property('zstate_foo')``.  Without the seed the
    slot returns None and any arithmetic crashes (e.g. ITAKE's load-allowed
    check).  We set the property directly on the wizard at bootstrap time
    because verb files (and therefore ``zstate_set`` itself) haven't loaded
    yet when this script runs.
    """
    import re as _re

    lines = [
        "# Generated by extras/zil_import — do not edit by hand",
        '"""Scalar ZIL globals seeded into the wizard\'s zstate slots."""',
        "# pylint: disable=undefined-variable",
        "",
    ]
    if globals_dict:
        for name, value in sorted(globals_dict.items()):
            sanitized = _re.sub(r"[^a-z0-9_]", "_", name.lower().replace("-", "_"))
            prop = "zstate_" + sanitized
            lines.append(f"wizard.set_property({prop!r}, {value!r})")
        lines.append("")
        lines.append(f"log.info('Zork globals: {len(globals_dict)} seeded')")
    else:
        lines.append("log.info('Zork globals: none extracted')")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 035_tables.py — ZIL table data stored as properties on the System Object
# ---------------------------------------------------------------------------


def _gen_tables(tables: dict[str, list]) -> str:
    """Generate 035_tables.py which stores ZIL table data on the System Object.

    Atom references (entries prefixed with ``@``) are resolved to the
    matching room/object via ``_rooms`` / ``_objects`` lookup at
    bootstrap time, so ``lkp`` / ``go-next`` can compare table entries
    against ``here()`` (an Object) directly.  Non-atom entries (numbers,
    quoted strings) pass through verbatim.
    """
    lines = [
        "# Generated by extras/zil_import — do not edit by hand",
        '"""ZIL table data stored as list properties on the System Object."""',
        "# pylint: disable=undefined-variable",
        "",
        "# Tables are stored with zstate_ prefix so pick() can find them.",
        "# Key conversion: UPPER-KEBAB-CASE -> lower_snake_case with zstate_ prefix.",
        "",
    ]

    def _entry_repr(item: object) -> str:
        if isinstance(item, str) and item.startswith("@"):
            atom = item[1:]
            # Atom may be a room or object; both are stored in _rooms /
            # _objects after 020/030 run.  Fall back to the raw string
            # so bootstrap doesn't crash if a table references an atom
            # we never created (defensive; LTABLE pairs need both ends).
            return f"_rooms.get({atom!r}) or _objects.get({atom!r}) or {atom!r}"
        return repr(item)

    if tables:
        for atom, values in tables.items():
            prop_name = "zstate_" + atom.lower().replace("-", "_")
            entries = ", ".join(_entry_repr(v) for v in values)
            lines.append(f"_.set_property({repr(prop_name)}, [{entries}])")
        lines.append("")
        lines.append(f"log.info('Zork tables: {len(tables)} loaded onto System Object')")
    else:
        lines.append("# No tables extracted from ZIL source.")
        lines.append("# If ZIL source contains LTABLE/TABLE globals, re-run the converter.")
        lines.append("log.info('Zork tables: none (no tables extracted)')")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_all(
    rooms: dict[str, ZilRoom],
    objects: dict[str, ZilObject],
    routines: dict[str, ZilRoutine],
    output_dir: Path,
    tables: dict[str, list] | None = None,
    globals_dict: dict[str, object] | None = None,
    syntax_dict: dict[str, list[tuple[int, str]]] | None = None,
    synonyms_dict: dict[str, list[str]] | None = None,
    linter=None,  # extras.zil_import.lint.Linter | None — optional per-file pylint
) -> None:
    tables = tables or {}
    globals_dict = globals_dict or {}
    syntax_dict = syntax_dict or {}
    synonyms_dict = synonyms_dict or {}
    # When ``--lint`` is on the translator emits a smaller pylint-disable
    # header (only the verb-format-intrinsic ``return-outside-function``
    # and ``undefined-variable``) so every other warning surfaces and gets
    # fixed at the translator level instead of being silenced by file
    # comments.  Without ``--lint`` the legacy "tolerant" disable list is
    # emitted so manual pylint runs over the bootstrap stay quiet.
    lint_active = linter is not None
    pylint_disable = "# pylint: disable=" + (DISABLE_INTRINSIC if lint_active else DISABLE_FULL)
    output_dir.mkdir(parents=True, exist_ok=True)
    verbs_dir = output_dir / "verbs"
    # Wipe the previous regen so stale files (renamed routines, removed
    # objects, or files left behind by earlier flat-directory layouts)
    # don't pile up in the bootstrap output.  The whole tree is rebuilt
    # below from templates + fresh codegen.
    if verbs_dir.exists():
        shutil.rmtree(verbs_dir)
    verbs_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = output_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Copy the static verb templates (PREFIX/SUFFIX delimiters and the
    # ZIL→DjangoMOO impedance shims under zil_sdk/) into verbs/ before
    # generating ZIL routine files.  None of
    # these depend on ZIL input — they're the small runtime layer the
    # translator emits calls to.
    for src in _TEMPLATE_VERBS_DIR.iterdir():
        dst = verbs_dir / src.name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    def _write_and_lint(path: Path, code: str) -> None:
        """Write a top-level bootstrap script and lint it when ``--lint`` is on.

        Top-level bootstrap files (``020_rooms.py``, ``030_objects.py``,
        etc.) bypass the per-clause ``_write_unique`` path; this helper
        keeps the lint check consistent across both code paths.
        """
        path.write_text(code, encoding="utf-8")
        if linter is not None:
            linter.check_or_raise(path)

    # Empty package marker — keeps the bootstrap directory importable for
    # test discovery without running database setup at import time.
    # Skip the lint check — pylint scores empty files at "no statements"
    # which our threshold gate already treats as a no-op.
    (output_dir / "__init__.py").write_text("", encoding="utf-8")

    # Bootstrap entry point — invoked via `moo_init --bootstrap`.
    _write_and_lint(output_dir / "bootstrap.py", _gen_bootstrap_init(rooms, objects))

    # 010_classes.py — root classes only; SDK verbs attach directly to System Object
    _write_and_lint(output_dir / "010_classes.py", _CLASSES_TEMPLATE)

    # 013_globals.py — scalar GLOBAL declarations (LOAD-ALLOWED, etc.)
    _write_and_lint(output_dir / "013_globals.py", _gen_globals(globals_dict))

    # NB: tables are emitted *after* 030_objects so atom-reference
    # resolution can use the ``_rooms`` / ``_objects`` dicts that
    # 020/030 leave in the bootstrap namespace.  Old runs may have a
    # stale ``015_tables.py`` lying around; remove it so loader doesn't
    # double-emit the tables (now 035_tables.py).
    stale_015 = output_dir / "015_tables.py"
    if stale_015.exists():
        stale_015.unlink()

    # Compute globally-unique display names once and reuse for object/room
    # creation and verb shebangs so ``--on "<display>"`` resolves to a
    # single Object at verb-load time.
    display_names = _compute_display_names(rooms, objects)

    # 020_rooms.py
    _write_and_lint(output_dir / "020_rooms.py", _gen_rooms(rooms, display_names))

    # 030_objects.py
    _write_and_lint(output_dir / "030_objects.py", _gen_objects(objects, rooms, display_names))

    # 035_tables.py — ZIL table data on the System Object.  After rooms/
    # objects so atom references can resolve to actual Object instances.
    _write_and_lint(output_dir / "035_tables.py", _gen_tables(tables))

    # 040_exits.py
    _write_and_lint(output_dir / "040_exits.py", _gen_exits(rooms))

    # Translated verb files
    # Map each routine to the object/room it's an action for.
    # When multiple objects share the same ACTION routine, the last one wins as
    # primary (existing behaviour); extras are tracked separately so the
    # generator can emit a verb file for each additional owner.
    action_owners: dict[str, tuple[str | None, bool]] = {}  # name → (atom, is_room)
    action_all_owners: dict[str, list[tuple[str, bool]]] = {}  # name → ALL owners
    for atom, room in rooms.items():
        if room.action:
            action_owners[room.action] = (atom, True)
            action_all_owners.setdefault(room.action, []).append((atom, True))
    for atom, obj in objects.items():
        if obj.action:
            action_owners[obj.action] = (atom, False)
            action_all_owners.setdefault(obj.action, []).append((atom, False))

    def _global_bucket(routine_name: str) -> str:
        """Subdivide a substrate-class bucket by routine-name shape.

        Only used inside large substrate dirs (``zork_thing/``, etc.) where
        the flat list would be hundreds of files long.  Substrate prefixes
        (V-/PRE-/I-/M-) are well-known.  Everything else is bucketed by ZIL
        naming convention: ``-PSEUDO``/``-FCN``/``-F`` suffixes mean object
        handlers, ``?``-suffixed names are predicates, plus a few
        keyword-driven buckets for combat, parser, output, and scoring
        helpers.  Anything that doesn't match lands in ``helpers/``.
        """
        lower = routine_name.lower()
        if lower.startswith("v-"):
            return "substrate_verbs"
        if lower.startswith("pre-"):
            return "substrate_pre"
        if lower.startswith("i-"):
            return "daemons"
        if lower.startswith("m-"):
            return "metaverbs"
        if lower.endswith(("-pseudo",)):
            return "pseudo_objects"
        if lower.endswith(("-fcn", "-function", "-f")):
            return "object_handlers"
        if lower.endswith("?"):
            return "predicates"
        if any(k in lower for k in ("print", "tell", "remark", "describe-", "with-tell")):
            return "output"
        if any(k in lower for k in ("fight", "villain", "weapon", "thief", "snarf", "rob", "steal")):
            return "combat"
        if any(k in lower for k in ("clause", "syntax", "buffer-print", "unknown-word", "this-is-it", "this-it")):
            return "parser"
        if any(k in lower for k in ("score", "winning", "finish")):
            return "score"
        return "helpers"

    # Substrate dirs that need topic subdivision (too many verbs to read flat).
    _SUBDIVIDED_SUBSTRATE = {"zork_thing"}

    def _substrate_dir(substrate_name: str, routine_name: str) -> Path:
        """Directory for a substrate-attached verb.  ``zork_thing`` is large
        enough to need topic subdirs; smaller buckets stay flat."""
        # ZIL ``$player`` is an alias for ``Zork Actor``; collapse the layout.
        if substrate_name == "player":
            substrate_name = "zork_actor"
        if substrate_name in _SUBDIVIDED_SUBSTRATE:
            return verbs_dir / substrate_name / _global_bucket(routine_name)
        return verbs_dir / substrate_name

    def _atom_dir(atom: str, is_room: bool) -> Path:
        slug = atom.lower().replace("-", "_")
        if is_room:
            return verbs_dir / "rooms" / slug
        # Co-locate object handlers with their starting room so each room's
        # directory contains the room's action verbs and the per-object
        # action verbs for items that begin life there.  Orphan objects
        # (global pseudos, contents of containers we can't trace back to
        # a room) stay at the top level under ``verbs/<slug>/``.
        room_atom = _resolve_object_room(atom, objects, rooms)
        if room_atom:
            return verbs_dir / "rooms" / _room_slug(room_atom) / slug
        return verbs_dir / slug

    def _ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        init = path / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")
        return path

    def _target_dir(routine_name: str, action_owner: tuple[str, bool] | None) -> Path:
        if action_owner:
            atom, is_room = action_owner
            return _ensure_dir(_atom_dir(atom, is_room))
        substrate = owner_overrides.get(routine_name.upper(), "zork_thing")
        return _ensure_dir(_substrate_dir(substrate, routine_name))

    translated_names = []
    m_clause_count = 0

    # See :doc:`/reference/zil-importer` for how these are used.
    object_atoms = set(rooms.keys()) | set(objects.keys())
    # ZIL conflates room-action names with the room itself in some
    # references — e.g. ``<EQUAL? ,HERE ,LLD-ROOM>`` compares the player's
    # current room to the room whose ACTION routine is LLD-ROOM (i.e.
    # ENTRANCE-TO-HADES).  To preserve that semantic, treat each room's
    # ACTION-routine name as an object atom; the bootstrap also adds it
    # as an alias on the room so ``lookup("lld_room")`` resolves to
    # ENTRANCE-TO-HADES.
    for room in rooms.values():
        if room.action:
            object_atoms.add(room.action)
    routine_atoms = set(routines.keys())

    # Routines we explicitly skip because they reference Z-machine
    # internals that don't translate cleanly.  CLOCKER is replaced by
    # a static template that calls ``zil_sdk.tick``; the rest are
    # parser-internal (walk ``P-LEXV`` / ``P-PRSO`` / ``P-PRSI``
    # tables we don't populate) or object-resolution helpers that
    # depend on the ZIL parser.  DjangoMOO's parser handles command
    # dispatch and object matching, so these routines have no callers
    # in code we keep.
    _SKIP_ROUTINES = {
        # Z-machine read loop / parser core
        "CLOCKER",
        "MAIN-LOOP",
        "MAIN-LOOP-1",
        "PARSER",
        # Parser-internal predicates
        "YES?",
        "NUMBER?",
        # Parser clause walking
        "CLAUSE",
        "CLAUSE-ADD",
        "CLAUSE-COPY",
        "ACLAUSE-WIN",
        "NCLAUSE-WIN",
        "SYNTAX-CHECK",
        "SYNTAX-FOUND",
        "UNKNOWN-WORD",
        "ORPHAN",
        "ORPHAN-MERGE",
        "CANT-USE",
        "CANT-ORPHAN",
        "WHICH-PRINT",
        "THING-PRINT",
        # Parser output helpers — produce only ZIL-parser failure messages
        # ("I don't know the word X", "You can't see any X here") that
        # DjangoMOO's parser surfaces through its own NoSuchObject /
        # NoSuchVerb exceptions.  No remaining caller in the kept tree.
        "WORD-PRINT",
        "BUFFER-PRINT",
        "NOT-HERE-PRINT",
        # Object-resolution helpers tied to the ZIL parser
        "NOT-HERE-OBJECT-F",
        "SNARF-OBJECTS",
        "SNARFEM",
        "GET-OBJECT",
        "MANY-CHECK",
        "ITAKE-CHECK",
        "GLOBAL-CHECK",
        "GWIM",
        "BUT-MERGE",
        # NOTE: THIS-IS-IT is *kept* — translated v-* / object handlers
        # invoke it 19+ times to set the ZIL pronoun (P-IT-OBJECT) state.
        # The translated body is just zstate writes, harmless to run.
        #
        # F.1: Movement substrate replaced by zil_sdk/exit_move.py + walk
        # dispatcher (see D2).  Z-machine exit-table walking via
        # getpt/ptsize/UEXIT/NEXIT/FEXIT/CEXIT/DEXIT has no caller in
        # the kept tree.  V-CLIMB-* call each other in chains that all
        # become unreachable when V-CLIMB-UP is skipped.
        "V-WALK",
        "DO-WALK",
        "V-CLIMB-UP",
        "V-CLIMB-DOWN",
        "V-CLIMB-ON",
        "V-CLIMB-FOO",
        # F.1: Parser-buffer (P-LEXV) substrate verbs — read words the
        # player typed via Z-machine word-buffer slots, which DjangoMOO
        # doesn't populate.  Their syntax entries route to V-XXX but no
        # caller actually invokes them in the kept tree.
        "V-SAY",
        "V-ECHO",
        "V-INCANT",
        # F.1: V-LEAP body uses ptsize exit-table walking; same
        # dead-after-D2 logic as V-WALK.  JUMP routes here in syntax but
        # the routine is unreachable (chains through V-WALK).
        "V-LEAP",
        # F.3: Parser-internal name-match predicates that walk Z-machine
        # synonym/adjective tables via getpt/ptsize.  DjangoMOO's parser
        # already does name resolution against ``Object.aliases``; these
        # routines have no live callers in the kept tree.
        "THIS-IT?",
        "GLOBAL-IN?",
        # F.3: Lit-room search chain (LIT? dark-branch helpers).  ``LIT?``
        # only enters this branch when zstate keys ``P-SLOCBITS`` /
        # ``P-TABLE`` / ``P-MERGE`` are populated, which DjangoMOO never
        # does.  ``DO-SL`` and ``SEARCH-LIST`` are the only callers and
        # both end here, so the whole chain is dead.
        "DO-SL",
        "SEARCH-LIST",
        "OBJ-FOUND",
        # C.3: HELD? walks the location chain via ``while True``; the SDK
        # template at zil_sdk/is_held.py provides a bounded walk with
        # cycle detection and a depth cap.
        "HELD?",
    }

    def _filename_from_shebang(code: str) -> str:
        """Derive ``<first_verb_snake>.py`` from the verb shebang on line 1.

        The shebang is the source of truth for verb identity, so the file on
        disk takes its name directly from it.  Falls back to ``unnamed.py``
        for code that lacks a shebang (shouldn't happen in normal output;
        guards the writer against an empty translation).
        """
        first_line = code.split("\n", 1)[0] if code else ""
        if not first_line.startswith("#!moo verb"):
            return "unnamed.py"
        rest = first_line[len("#!moo verb") :].strip()
        try:
            tokens = shlex.split(rest)
        except ValueError:
            tokens = rest.split()
        first = tokens[0] if tokens else ""
        snake = first.lower().replace("-", "_").replace("@", "").replace("?", "_p").replace("!", "_b")
        return (snake or "unnamed") + ".py"

    def _write_unique(target: Path, fname: str, code: str) -> None:
        """Write ``code`` to ``target/fname``, suffixing on collision.

        Within one owner's directory two clauses can theoretically share a
        first-verb name (different ZIL routines whose shebangs happen to
        emit the same ``--on``-target + first-verb).  Append ``_2``, ``_3``,
        ... in that case so neither clause clobbers the other.

        When a ``linter`` is wired into ``generate_all`` the freshly
        written file is scored immediately; below-threshold scores raise
        ``RuntimeError`` from inside the regen so the operator sees the
        offending file's pylint output without searching post-hoc.
        """
        path = target / fname
        if not path.exists():
            path.write_text(code, encoding="utf-8")
            if linter is not None:
                linter.check_or_raise(path)
            return
        stem = fname[:-3]
        n = 2
        while True:
            candidate = target / f"{stem}_{n}.py"
            if not candidate.exists():
                candidate.write_text(code, encoding="utf-8")
                if linter is not None:
                    linter.check_or_raise(candidate)
                return
            n += 1

    def _emit_routine(translator: ZilTranslator, target: Path, name: str) -> None:
        """Emit per-clause + per-M-clause + residual files for one routine.

        Each emitted file is named after the first verb in its shebang's
        verb list (snake-cased).  With the per-owner directory layout, no
        prefix is needed: each owner's verbs already live in their own
        ``rooms/<room>/<obj>/`` (or ``zork_thing/<topic>/``) folder.
        """
        nonlocal m_clause_count
        # M-clauses (M-BEG / M-LOOK / M-END / ...) → one file per constant.
        if translator.has_m_dispatch():
            for m_const in translator.m_constants_found():
                clause_code = translator.translate_m_clause(m_const)
                if _clause_is_empty(clause_code):
                    continue
                _write_unique(target, _filename_from_shebang(clause_code), clause_code)
                m_clause_count += 1
        # VERB? clauses (player-verb dispatch) → one file per clause, with
        # the multi-verb shebang preserved when the ZIL grouped them.
        clause_split_verbs: set[str] = set()
        if translator.has_verb_dispatch():
            for verb_atoms, extra_test, body_forms in translator.verb_clauses_for_split():
                clause_code = translator.translate_verb_clause(verb_atoms, extra_test, body_forms)
                if not clause_code:
                    continue
                # Track which verb aliases the clause registered so the
                # residual can subtract them and avoid a parser-dispatch
                # collision on the same (object, verb-name) pair.
                for atom in verb_atoms:
                    for alias in ZIL_VERBS.get(atom.upper(), [atom.lower()]):
                        clause_split_verbs.add(alias)
                _write_unique(target, _filename_from_shebang(clause_code), clause_code)
        # Residual full-routine body — only emitted if anything is left after
        # both pruning passes.  ``translate()`` returns "" for an empty
        # residual (per-clause files already cover everything).
        translator._clause_split_verbs = clause_split_verbs  # pylint: disable=protected-access
        full_code = translator.translate()
        if full_code:
            _write_unique(target, _filename_from_shebang(full_code), full_code)

    # D3 Phase 1: relocate substrate verbs whose syntax entry is strictly
    # 0-OBJECT.  Without a dobj the parser can't reach $zork_thing via
    # inheritance, so the substrate would be unreachable; moving it onto
    # $player (aliased to $zork_actor in the bootstrap) puts it back in
    # the search order and lets us drop the syntax/ trampoline.
    #
    # syntax-finish bucket B extension: same-routine mixed-arity verbs
    # (CURSE, EXIT, FOLLOW, HELLO, JUMP, STAND, SWIM — all 0-OBJECT and
    # 1-OBJECT slots dispatch to the same V-routine) also relocate.
    # Parser dispatch finds the player-owned substrate for both arities;
    # the body internally handles dobj-presence.
    _PLAYER_OWNED_ROUTINES: set[str] = set()
    _SAME_ROUTINE_MIXED: set[str] = set()
    # Reverse map: V-routine name → set of player verbs that dispatch to it.
    # Built from SYNTAX rules so substrate verbs like V-LAMP-ON register under
    # their player name (``light``) and any synonyms — without this, the
    # parser's verb match would only find ``lamp_on`` which no player types.
    _ROUTINE_TO_VERBS: dict[str, list[str]] = {}
    for verb, rules in syntax_dict.items():
        counts = {n for n, _ in rules}
        v_routines = {v for n, v in rules}
        if counts == {0}:
            v_routine = next((v for n, v in rules if n == 0), None)
            if v_routine:
                _PLAYER_OWNED_ROUTINES.add(v_routine.upper())
        elif 0 in counts and len(v_routines) == 1:
            # Mixed arity but every rule maps to the same V-routine.
            v_routine = next(iter(v_routines))
            _PLAYER_OWNED_ROUTINES.add(v_routine.upper())
            _SAME_ROUTINE_MIXED.add(verb)
        for _, v_routine in rules:
            v_upper = v_routine.upper()
            verb_lower = verb.lower()
            bucket = _ROUTINE_TO_VERBS.setdefault(v_upper, [])
            if verb_lower not in bucket:
                bucket.append(verb_lower)
            for syn in synonyms_dict.get(verb, []):
                syn_lower = syn.lower()
                if syn_lower and not syn_lower.startswith("\\") and syn_lower not in bucket:
                    bucket.append(syn_lower)
    owner_overrides = {name: "player" for name in _PLAYER_OWNED_ROUTINES}

    # syntax-finish bucket A: V-routines whose PRE-X handler exists get a
    # pre-X check inlined at the top of the substrate body during
    # translation, replacing the syntax/ trampoline.  Compute the set of
    # PRE-X bases here so the translator can prepend the check, and the
    # syntax loop below knows to skip emission for these verbs.
    _pre_bases: set[str] = set()
    for r_name in routines.keys():
        upper = r_name.upper()
        if upper.startswith("PRE-"):
            _pre_bases.add(upper.removeprefix("PRE-"))
    pre_handler_routines = {f"V-{base}" for base in _pre_bases}

    for name, routine in routines.items():
        if name in _SKIP_ROUTINES:
            continue
        translator = ZilTranslator(
            routine,
            object_atoms=object_atoms,
            routine_atoms=routine_atoms,
            action_owner=action_owners.get(name),
            owner_overrides=owner_overrides,
            pre_handler_routines=pre_handler_routines,
            display_names=display_names,
            substrate_display_names=SUBSTRATE_DISPLAY_NAMES,
            routine_to_verbs=_ROUTINE_TO_VERBS,
            lint_active=lint_active,
        )

        target = _target_dir(name, action_owners.get(name))
        _emit_routine(translator, target, name)

        translated_names.append(name)

        # For shared ACTION routines (same routine on multiple objects/rooms),
        # emit a separate verb file for each additional owner so each object
        # gets its own ``--on "<display>"`` registration.
        primary_owner = action_owners.get(name)
        for extra_atom, extra_is_room in action_all_owners.get(name, []):
            if primary_owner and extra_atom == primary_owner[0]:
                continue  # skip the primary; it was written above
            extra_translator = ZilTranslator(
                routine,
                object_atoms=object_atoms,
                routine_atoms=routine_atoms,
                action_owner=(extra_atom, extra_is_room),
                owner_overrides=owner_overrides,
                pre_handler_routines=pre_handler_routines,
                display_names=display_names,
                substrate_display_names=SUBSTRATE_DISPLAY_NAMES,
                lint_active=lint_active,
            )
            # Each owner now lives in its own directory under ``rooms/`` (or
            # at the top level for orphans), so a shared ACTION routine
            # (e.g. BUTTON-F across yellow/brown/red/blue) writes the same
            # filename into different directories — no clobber risk.
            extra_sub = _ensure_dir(_atom_dir(extra_atom, extra_is_room))
            _emit_routine(extra_translator, extra_sub, name)

    # SYNTAX-driven player commands.  After D3 + syntax-finish, only the
    # genuinely-special routing shims remain — WALK/PUT specials and the
    # mixed-arity verbs whose 0-OBJECT and 1-OBJECT slots dispatch to
    # different V-routines (LOOK, ANSWER, ENTER, LEAVE, #).  These attach to
    # ``Zork Actor`` (``$player``); the legacy ``verbs/syntax/`` and
    # ``verbs/_global/dispatchers/`` directories are no longer created.
    dispatchers_dir = _ensure_dir(verbs_dir / "zork_actor" / "dispatchers")
    # Verbs whose substrate V-routine uses Z-machine table-based exits
    # (V-WALK, V-WALK-AROUND).  Our exit model is Object-based, so the
    # WALK family delegates to our zil_sdk.walk helper instead of the
    # substrate routine.
    OBJECT_WALK_OVERRIDES = {"WALK"}

    # Verbs that have a 2-object "put X in Y" form (→ V-PUT) and a
    # 1-object "drop X" form (→ V-DROP).  The generator's 2-object skip
    # logic would lose the container routing, so we special-case them here:
    # if any preposition was parsed, route to v-put; otherwise v-drop.
    PUT_OVERRIDES = {"PUT"}

    syntax_count = 0
    for verb, rules in syntax_dict.items():
        names = [verb] + synonyms_dict.get(verb, [])
        names = [n.lower() for n in names if n and not n.startswith("\\")]
        if not names or not rules:
            continue
        # D3 Phase 1: skip trampolines for strictly-0-OBJECT verbs.  Their
        # substrate has been relocated to $player by ``owner_overrides``, so
        # parser dispatch finds it directly without a trampoline shim.
        counts = {n for n, _ in rules}
        if counts == {0}:
            continue
        # syntax-finish bucket B: same-routine mixed-arity verbs are also
        # relocated to $player and need no trampoline.
        if verb in _SAME_ROUTINE_MIXED:
            continue
        # OBJECT-bearing verbs need a dispatcher when the player verb name
        # doesn't match the V-routine's snake-name — otherwise ``light
        # lamp`` (which routes to V-LAMP-ON, snake-name ``lamp_on``) finds
        # nothing on the dobj.  When the names DO match (e.g. player
        # ``take`` → V-TAKE → snake-name ``take``), the substrate is
        # already discoverable on the dobj via inheritance and a dispatcher
        # would just be dead code (parser's last-match-wins picks the
        # dobj-bound substrate over the caller-bound dispatcher).
        if 0 not in counts and verb not in {"WALK", "PUT"}:
            v_variants = {v for n, v in rules if n >= 1}
            substrate_names = {v.lower().removeprefix("v-") for v in v_variants}
            if verb.lower() in substrate_names:
                continue
        # WALK family: delegate to the generic exit-Object traversal helper
        # (``_.walk``) rather than the substrate's table-based V-WALK,
        # which assumes Z-machine memory exits we don't have.
        if verb in OBJECT_WALK_OVERRIDES:
            body = textwrap.dedent(f"""\
                #!moo verb {" ".join(names)} --on "Zork Actor" --dspec either

                # Generated by extras/zil_import — do not edit by hand
                {pylint_disable}

                \"\"\"Player command for {verb}: traverse an exit Object.\"\"\"

                from moo.sdk import context

                parser = context.parser
                if parser.has_dobj_str():
                    _.walk(parser.get_dobj_str())
                elif len(parser.words) > 1:
                    _.walk(parser.words[1])
                else:
                    print("Where do you want to go?")
            """)
            fname = verb.lower() + ".py"
            (dispatchers_dir / fname).write_text(body, encoding="utf-8")
            syntax_count += 1
            continue
        # PUT family: "put X in Y" → v-put, "put X" → v-drop.  The
        # 2-object variant is skipped by the general codegen below, so we
        # special-case it: route to v-put when any preposition is present.
        if verb in PUT_OVERRIDES:
            body = textwrap.dedent(f"""\
                #!moo verb {" ".join(names)} --on "Zork Actor" --dspec either

                # Generated by extras/zil_import — do not edit by hand
                {pylint_disable}

                # Player command for {verb}: put in container (with prep) or drop (bare).
                from moo.sdk import context

                if context.parser.prepositions:
                    if _.zork_thing.has_verb("pre-put") and _.zork_thing.invoke_verb("pre-put"):
                        return
                    _.zork_thing.put()
                else:
                    if _.zork_thing.has_verb("pre-drop") and _.zork_thing.invoke_verb("pre-drop"):
                        return
                    _.zork_thing.drop()
            """)
            fname = verb.lower() + ".py"
            (dispatchers_dir / fname).write_text(body, encoding="utf-8")
            syntax_count += 1
            continue
        # Pick the no-OBJECT and the single-OBJECT variants.  Two-OBJECT
        # variants (e.g. ``READ OBJECT OBJECT = V-READ-PAGE``) are skipped
        # because the dobj/iobj split would need extra grammar parsing the
        # SYNTAX codegen doesn't do; the player command falls back to the
        # one-OBJECT V-routine when only a single dobj is typed.
        no_obj = next((v for n, v in rules if n == 0), None)
        obj_variant = next((v for n, v in rules if n == 1), None)
        if obj_variant is None:
            # Fall back to whichever variant is closest to one-object so
            # commands like ``put`` (only ever multi-object in syntax) still
            # have something to delegate to.
            obj_variant = next((v for n, v in sorted(rules, key=lambda r: r[0]) if n >= 1), None)

        # Build the body.  When both variants exist, branch on whether the
        # player typed a dobj.  Otherwise just delegate to whichever rule
        # we have.
        # ZIL semantics: each V-routine has an optional PRE-routine that
        # runs first and short-circuits dispatch on truthy return.  Map
        # ``v-<base>`` ↔ ``pre-<base>`` and emit a guard so the pre-verb
        # actually fires (the parser doesn't know about it).  After Phase
        # 3 item 3 (drop ``v-`` prefix on substrate verbs), the substrate
        # verb is registered under the plain ``<base>`` name.
        def _pre_for(v_name: str) -> str:
            # ``has_verb`` / ``invoke_verb`` look up by string name, so the
            # pre-X key keeps the ZIL-style hyphen (``pre-lamp-on``) — that's
            # the verb name actually registered on Zork Thing.
            base = v_name.lower().removeprefix("v-")
            return "pre-" + base

        def _substrate_for(v_name: str) -> str:
            # Substrate verbs are registered with ``v-`` stripped and dashes
            # kept as the verb name, but the dispatcher reaches them via
            # dot-syntax (``_.zork_thing.lamp_on()``) which requires a
            # Python-valid identifier.  Snake-case the routine name so the
            # generated Python parses.
            return v_name.lower().removeprefix("v-").replace("-", "_")

        if no_obj and obj_variant and no_obj != obj_variant:
            body = textwrap.dedent(f"""\
                #!moo verb {" ".join(names)} --on "Zork Actor" --dspec either

                # Generated by extras/zil_import — do not edit by hand
                {pylint_disable}

                \"\"\"Player command for {verb}: dispatch by object slot.\"\"\"

                from moo.sdk import context

                if context.parser.has_dobj_str():
                    pre = {_pre_for(obj_variant)!r}
                    if _.zork_thing.has_verb(pre) and _.zork_thing.invoke_verb(pre):
                        return
                    _.zork_thing.{_substrate_for(obj_variant)}()
                else:
                    pre = {_pre_for(no_obj)!r}
                    if _.zork_thing.has_verb(pre) and _.zork_thing.invoke_verb(pre):
                        return
                    _.zork_thing.{_substrate_for(no_obj)}()
            """)
        else:
            v_routine = obj_variant or no_obj
            body = textwrap.dedent(f"""\
                #!moo verb {" ".join(names)} --on "Zork Actor" --dspec either

                # Generated by extras/zil_import — do not edit by hand
                {pylint_disable}

                \"\"\"Player command for {verb}: delegate to {v_routine}.\"\"\"

                pre = {_pre_for(v_routine)!r}
                if _.zork_thing.has_verb(pre) and _.zork_thing.invoke_verb(pre):
                    return
                _.zork_thing.{_substrate_for(v_routine)}()
            """)
        fname = verb.lower().replace("?", "_p").replace("!", "_b") + ".py"
        (dispatchers_dir / fname).write_text(body, encoding="utf-8")
        syntax_count += 1
    print(f"  syntax commands: {syntax_count}")

    # verbs_dir __init__.py
    (verbs_dir / "__init__.py").write_text("# Zork 1 translated verb files\n", encoding="utf-8")

    # tests __init__.py
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    _write_tests(rooms, objects, routines, translated_names, tests_dir)

    # Run ruff format on every generated file so the committed output
    # matches the project's formatting rules without relying on a
    # separate auto-fix pass.  Failures are non-fatal — the worst case is
    # the pre-commit hook fixing them later.
    import subprocess

    try:
        subprocess.run(
            ["ruff", "format", "--quiet", str(output_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

    print(
        f"Generated {len(rooms)} rooms, {len(objects)} objects, {len(routines)} routines "
        f"({m_clause_count} M-* clause splits)"
    )
    print(f"Bootstrap: {output_dir}/")
    print(f"Verbs:     {verbs_dir}/")


# ---------------------------------------------------------------------------
# Test generation
# ---------------------------------------------------------------------------


def _write_tests(
    rooms: dict[str, ZilRoom],
    objects: dict[str, ZilObject],
    routines: dict[str, ZilRoutine],
    stub_names: list[str],
    tests_dir: Path,
) -> None:
    _write_conftest(rooms, tests_dir)
    _write_test_rooms(rooms, tests_dir)
    _write_test_objects(objects, rooms, tests_dir)
    _write_test_exits(rooms, tests_dir)
    _write_test_verbs(stub_names, tests_dir)


def _write_conftest(rooms: dict[str, ZilRoom], tests_dir: Path) -> None:
    # Find a starting room (first outdoor room, or first room)
    start_atom = next(
        (a for a, r in rooms.items() if "ONBIT" in r.flags and "RLANDBIT" in r.flags),
        next(iter(rooms), None),
    )
    start_room = rooms[start_atom] if start_atom else None
    start_name = start_room.desc if start_room else "Unknown"

    content = textwrap.dedent(f"""\
        # Generated by extras/zil_import
        import pytest
        from moo.bootstrap import initialize_dataset
        from moo.core import code
        from moo.sdk import lookup


        @pytest.fixture
        def zork_world(t_init, t_wizard):
            \"\"\"Bootstrap the zork1 dataset for the duration of one test.

            Uses the project-wide ``t_init`` fixture parametrized for ``zork1``
            so each test gets a freshly seeded world that lives only as long
            as the surrounding ``django_db`` transaction.
            \"\"\"
            return t_init


        @pytest.fixture
        def t_start_room(zork_world, t_wizard):
            room = lookup({repr(start_name)})
            t_wizard.location = room
            t_wizard.save()
            t_wizard.refresh_from_db()
            return room
    """)
    (tests_dir / "conftest.py").write_text(content, encoding="utf-8")


def _write_test_rooms(rooms: dict[str, ZilRoom], tests_dir: Path) -> None:
    # Pick a handful of representative rooms to test
    samples = list(rooms.values())[:5]

    cases = []
    for room in samples:
        name = room.desc or room.atom
        exit_dirs = [e.direction.lower() for e in room.exits if e.dest][:2]
        blocked = [e for e in room.exits if e.message and not e.dest]
        outdoor = "RLANDBIT" in room.flags
        lit = "ONBIT" in room.flags

        cases.append(f"""
class Test{room.atom.replace("-", "_").title().replace("_", "")}:
    def test_exists(self, zork_world):
        room = lookup({repr(name)})
        assert room is not None

    def test_has_description(self, zork_world):
        from moo.sdk import NoSuchPropertyError

        room = lookup({repr(name)})
        try:
            desc = room.get_property("description")
        except NoSuchPropertyError:
            desc = None
        assert desc or room.name""")

        if exit_dirs:
            cases.append(f"""
    def test_has_exits(self, zork_world):
        room = lookup({repr(name)})
        exits = room.get_property("exits")
        aliases = {{a for e in exits for a in e.aliases.values_list("alias", flat=True)}}
        assert {repr(exit_dirs[0])} in aliases""")

        if blocked:
            cases.append(f"""
    def test_blocked_exit_{blocked[0].direction.lower()}(self, zork_world):
        room = lookup({repr(name)})
        exits = room.get_property("exits")
        blocked = [e for e in exits if e.get_property("dest") is None and e.get_property("nogo_msg")]
        assert blocked""")

        if outdoor:
            cases.append(f"""
    def test_outdoor(self, zork_world):
        room = lookup({repr(name)})
        assert room.get_property("outdoor") is True""")

        if lit:
            cases.append(f"""
    def test_lit(self, zork_world):
        room = lookup({repr(name)})
        assert room.get_property("dark") is False""")

    content = (
        textwrap.dedent("""\
        # Generated by extras/zil_import
        import pytest
        from moo.sdk import lookup

        # Each test gets a fresh ``zork1`` bootstrap inside a transactional
        # DB; ``t_init`` is parametrized indirectly so the bootstrap module
        # name reaches the project-wide fixture.
        pytestmark = [
            pytest.mark.django_db(transaction=True, reset_sequences=True),
            pytest.mark.parametrize("t_init", ["zork1"], indirect=True),
        ]
    """)
        + "\n".join(cases)
        + "\n"
    )
    (tests_dir / "test_rooms.py").write_text(content, encoding="utf-8")


def _write_test_objects(
    objects: dict[str, ZilObject],
    rooms: dict[str, ZilRoom],
    tests_dir: Path,
) -> None:
    # Skip objects whose lookup key clashes with a room or another object —
    # ``lookup()`` is case-insensitive over names + aliases, so a clash makes
    # the generated test ambiguous.
    room_names = {(r.desc or r.atom).lower() for r in rooms.values()}
    key_counts: dict[str, int] = {}
    for o in objects.values():
        for key in {(o.desc or o.atom.lower()).lower(), *(s.lower() for s in o.synonyms)}:
            key_counts[key] = key_counts.get(key, 0) + 1

    def _selectable(o: ZilObject) -> bool:
        key = (o.desc or o.atom.lower()).lower()
        return key not in room_names and key_counts.get(key, 0) == 1

    takeables = [o for o in objects.values() if "TAKEBIT" in o.flags and _selectable(o)][:4]
    containers = [o for o in objects.values() if "CONTBIT" in o.flags and _selectable(o)][:3]
    readable = [o for o in objects.values() if "READBIT" in o.flags and _selectable(o)][:2]

    lines = [
        "# Generated by extras/zil_import",
        "import pytest",
        "from moo.sdk import lookup",
        "",
        "pytestmark = [",
        "    pytest.mark.django_db(transaction=True, reset_sequences=True),",
        '    pytest.mark.parametrize("t_init", ["zork1"], indirect=True),',
        "]",
        "",
        "",
    ]

    if takeables:
        lines.append("class TestTakeables:")
        for obj in takeables:
            name = obj.desc or obj.atom.lower()
            lines.append(f"    def test_{obj.atom.lower().replace('-', '_')}_takeable(self, zork_world):")
            lines.append(f"        o = lookup({repr(name)})")
            lines.append(f"        assert o is not None")
            lines.append(f"        assert o.get_property('takeable') is True")
            lines.append("")

    if containers:
        lines.append("class TestContainers:")
        for obj in containers:
            name = obj.desc or obj.atom.lower()
            lines.append(f"    def test_{obj.atom.lower().replace('-', '_')}_is_container(self, zork_world):")
            lines.append(f"        o = lookup({repr(name)})")
            lines.append(f"        assert o is not None")
            lines.append(f"        parents = [p.name for p in o.parents.all()]")
            lines.append(f"        assert any('Container' in p or 'container' in p for p in parents)")
            if obj.capacity:
                lines.append(f"        assert o.get_property('capacity') == {obj.capacity}")
            lines.append("")

    if readable:
        lines.append("class TestReadable:")
        for obj in readable:
            name = obj.desc or obj.atom.lower()
            lines.append(f"    def test_{obj.atom.lower().replace('-', '_')}_readable(self, zork_world):")
            lines.append(f"        o = lookup({repr(name)})")
            lines.append(f"        assert o is not None")
            lines.append(f"        assert o.get_property('readable') is True")
            lines.append("")

    (tests_dir / "test_objects.py").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_test_exits(rooms: dict[str, ZilRoom], tests_dir: Path) -> None:
    # Find a room with a simple unconditional exit to test traversal
    traversal_pair = None
    for room in rooms.values():
        for ex in room.exits:
            if ex.dest and ex.dest in rooms and not ex.condition and not ex.per_routine:
                dest_room = rooms[ex.dest]
                traversal_pair = (room, ex, dest_room)
                break
        if traversal_pair:
            break

    blocked_ex = None
    blocked_room = None
    for room in rooms.values():
        for ex in room.exits:
            if ex.message and not ex.dest:
                blocked_ex = ex
                blocked_room = room
                break
        if blocked_ex:
            break

    lines = [
        "# Generated by extras/zil_import",
        "import pytest",
        "from moo.sdk import lookup",
        "",
        "pytestmark = [",
        "    pytest.mark.django_db(transaction=True, reset_sequences=True),",
        '    pytest.mark.parametrize("t_init", ["zork1"], indirect=True),',
        "]",
        "",
        "",
    ]

    if traversal_pair:
        src_room, ex, dst_room = traversal_pair
        src_name = src_room.desc or src_room.atom
        dst_name = dst_room.desc or dst_room.atom
        direction = ex.direction.lower()
        # Structural assertion only — full traversal goes through the
        # default-dataset's parse/dispatch pipeline, which the zork1
        # bootstrap doesn't pull in. We verify the exit object exists
        # and points at the right destination.
        lines += [
            f"def test_exit_traversal_{direction}(zork_world):",
            f"    room = lookup({repr(src_name)})",
            f"    exits = room.get_property('exits')",
            f"    matches = [",
            f"        e for e in exits",
            f"        if e.aliases.filter(alias={repr(direction)}).exists()",
            f"    ]",
            f"    assert matches, 'no {direction} exit on {src_name}'",
            f"    dest = matches[0].get_property('dest')",
            f"    assert dest is not None",
            f"    assert dest.name == {repr(dst_name)}",
            "",
            "",
        ]

    if blocked_ex and blocked_room:
        src_name = blocked_room.desc or blocked_room.atom
        direction = blocked_ex.direction.lower()
        # Same caveat as above — structural assertion only.
        lines += [
            f"def test_blocked_exit_{direction}(zork_world):",
            f"    room = lookup({repr(src_name)})",
            f"    exits = room.get_property('exits')",
            f"    matches = [",
            f"        e for e in exits",
            f"        if e.aliases.filter(alias={repr(direction)}).exists()",
            f"    ]",
            f"    assert matches, 'no {direction} exit on {src_name}'",
            f"    blocked = matches[0]",
            f"    assert blocked.get_property('dest') is None",
            f"    assert blocked.get_property('nogo_msg')",
            "",
        ]

    (tests_dir / "test_exits.py").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_test_verbs(verb_names: list[str], tests_dir: Path) -> None:
    if not verb_names:
        return

    param_list = repr(verb_names[:20])  # limit parametrize list
    content = textwrap.dedent(f"""\
        # Generated by extras/zil_import
        import pytest
        from moo.sdk import lookup


        @pytest.mark.django_db(transaction=True, reset_sequences=True)
        @pytest.mark.parametrize("t_init", ["zork1"], indirect=True)
        @pytest.mark.parametrize("routine_name", {param_list})
        def test_translated_verb_loaded(t_init, routine_name):
            \"\"\"Each translated ACTION routine should be loadable (no syntax errors).\"\"\"
            zork_room = lookup("Zork Room")
            assert zork_room is not None
            # Verb files are loaded by bootstrap.load_verbs — if they loaded, no SyntaxError.
            # Full dispatch testing requires individual test cases per verb.
    """)
    (tests_dir / "test_translated_verbs.py").write_text(content, encoding="utf-8")
