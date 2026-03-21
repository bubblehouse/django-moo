#!/usr/bin/env python3
"""
build_from_yaml.py - Generic YAML-driven MOO environment builder.

Builds themed multi-room environments from YAML environment definitions.

Usage:
    python build_from_yaml.py environments/moes-tavern.yaml
    python build_from_yaml.py --dry-run environments/moes-tavern.yaml
    python build_from_yaml.py --no-test environments/moes-tavern.yaml
    python build_from_yaml.py --hash environments/moes-tavern.yaml
    python build_from_yaml.py --no-hash environments/moes-tavern.yaml

Requires:
    pip install pexpect pyyaml
    DjangoMOO running locally (docker-compose up)
"""

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

import yaml

# Add parent directory to path for moo_ssh import
sys.path.insert(0, str(Path(__file__).parent))
from moo_ssh import MooSSH  # pylint: disable=wrong-import-position

# -----------------------------------------------------------------------------
# Helper Functions (reused from build_moes_tavern.py)
# -----------------------------------------------------------------------------


def obj_id(output):
    """Extract #N from @create output like 'Created #34 (bar stool)'."""
    m = re.search(r"Created (#\d+)", output)
    return m.group(1) if m else None


def create(moo, name, parent="$thing", obvious=False):
    """Create an object via @create and return its #N reference.

    Uses @create (not @eval create()) because @create output is captured
    synchronously via the ContextManager, while @eval output goes through
    player.tell() -> Kombu and arrives one command late.
    """
    escaped_name = name.replace('"', '\\"')
    escaped_parent = parent.replace('"', '\\"')
    output = moo.run(f'@create "{escaped_name}" from "{escaped_parent}" in the void')
    ref = obj_id(output)
    if not ref:
        print(f"  WARNING: could not get ID for '{name}' from: {output!r}", file=sys.stderr)
        return ref
    if obvious:
        moo.run(f'@eval "from moo.sdk import lookup; obj = lookup({ref[1:]}); obj.obvious = True; obj.save()"')
    return ref


def describe(moo, ref, desc):
    """Describe an object by #N reference (unambiguous)."""
    escaped_desc = desc.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    moo.run(f'@describe {ref} as "{escaped_desc}"')


def add_aliases(moo, ref, aliases):
    """Add aliases to an object using @alias verb."""
    for alias in aliases:
        escaped_alias = alias.replace('"', '\\"')
        moo.run(f'@alias {ref} as "{escaped_alias}"')


def move_to_room(moo, obj_ref, room_name):
    """
    Move an object from the void to a room using @eval with moveto().
    obj_ref: #N reference (unquoted)
    room_name: full room name (with hash if applicable)
    """
    obj_id_num = obj_ref.replace("#", "")
    escaped_room = room_name.replace('"', '\\"')
    moo.run(f'@eval "from moo.sdk import lookup; ' f'lookup({obj_id_num}).moveto(lookup(\\"{escaped_room}\\"))"')


def set_verb(moo, verb_name, obj_ref, code):
    """
    Create or update a verb using @edit ... with, passing multi-line code as
    a single \\n-escaped string. The @edit verb unescapes \\n back to newlines.

    obj_ref may be a #N id (not quoted) or a plain name (quoted).
    """
    # Escape backslashes first, then newlines, then double-quotes
    escaped = code.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    # #N refs are unquoted; plain names are quoted
    if str(obj_ref).startswith("#"):
        moo.run(f'@edit verb {verb_name} on {obj_ref} with "{escaped}"')
    else:
        moo.run(f'@edit verb {verb_name} on "{obj_ref}" with "{escaped}"')


# -----------------------------------------------------------------------------
# YAML Loading and Validation
# -----------------------------------------------------------------------------


def load_environment(yaml_path):
    """Load and validate YAML environment file."""
    with open(yaml_path, encoding="utf-8") as f:
        env = yaml.safe_load(f)

    # Validate required sections
    required = ["metadata", "rooms"]
    for section in required:
        if section not in env:
            raise ValueError(f"Missing required section: {section}")

    # Validate metadata fields
    metadata = env["metadata"]
    if "name" not in metadata:
        raise ValueError("metadata.name is required")

    return env


def generate_hash():
    """Generate unique 6-character hash for this build."""
    return hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]


def add_hash_suffix(name, run_hash, use_hash):
    """Add hash suffix to object/room name if use_hash is True."""
    if use_hash and run_hash:
        return f"{name} [{run_hash}]"
    return name


# -----------------------------------------------------------------------------
# Build Phase Functions
# -----------------------------------------------------------------------------


def teleport_to(moo, room_name):
    """Teleport the player to a room by name using @eval."""
    escaped = room_name.replace('"', '\\"')
    moo.run(
        f'@eval "from moo.sdk import lookup, context; '
        f'context.player.location = lookup(\\"{escaped}\\"); '
        f'context.player.save()"'
    )


def build_rooms(moo, env, run_hash, use_hash):
    """
    Create all rooms and exits.

    Phase 1: Create every room in the void (no navigation required).
    Phase 2: Teleport to each room, describe it, and tunnel all exits.
             All rooms already exist by this point, so @tunnel works for
             every exit regardless of direction or graph depth.

    Returns: room_map dict {original_name: hash_suffixed_name}
    """
    rooms = env["rooms"]
    room_map = {}

    if not rooms:
        return room_map

    # Phase 1: Create all rooms in the void
    print("  Creating rooms:", file=sys.stderr)
    for room_def in rooms:
        room_name = add_hash_suffix(room_def["name"], run_hash, use_hash)
        room_map[room_def["name"]] = room_name
        escaped = room_name.replace('"', '\\"')
        moo.run(f'@create "{escaped}" from "$room" in the void')
        print(f"    {room_name}", file=sys.stderr)

    # Phase 2: Teleport to each room, describe it, wire exits
    print("  Describing rooms and wiring exits:", file=sys.stderr)
    for room_def in rooms:
        room_name = room_map[room_def["name"]]
        teleport_to(moo, room_name)

        escaped_desc = room_def["description"].replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        moo.run(f'@describe here as "{escaped_desc}"')

        for exit_def in room_def.get("exits", []):
            direction = exit_def["direction"]
            to_room = exit_def["to"]
            # Use hash name if this room is in our map, otherwise use as-is
            # (allows exits to pre-existing rooms outside this environment)
            to_room_hash = room_map.get(to_room, to_room)
            escaped_to = to_room_hash.replace('"', '\\"')
            moo.run(f'@tunnel {direction} to "{escaped_to}"')
            print(f"    {room_name} -{direction}-> {to_room_hash}", file=sys.stderr)

    return room_map


def build_objects(moo, env, run_hash, use_hash, room_map):
    """
    Create all objects in all rooms.

    Returns: obj_refs dict mapping (room, name) -> #N reference
    """
    obj_refs = {}
    objects = env.get("objects", {})
    parent = env["metadata"].get("base_parent", "$thing")

    for room_name, objs in objects.items():
        room_hash_name = room_map.get(room_name, room_name)
        refs_to_move = []

        print(f"  Creating objects for: {room_name}", file=sys.stderr)

        for obj_spec in objs:
            name = obj_spec["name"]
            desc = obj_spec.get("description", "")
            aliases = obj_spec.get("aliases", [])
            quantity = obj_spec.get("quantity", 1)
            obj_parent = obj_spec.get("parent", parent)
            obj_obvious = obj_spec.get("obvious", False)

            # Create object(s)
            for i in range(quantity):
                hash_name = add_hash_suffix(name, run_hash, use_hash)
                ref = create(moo, hash_name, obj_parent, obvious=obj_obvious)

                if not ref:
                    continue

                # Only describe the first one
                if i == 0 and desc:
                    describe(moo, ref, desc)

                # Add aliases
                if aliases:
                    add_aliases(moo, ref, aliases)

                refs_to_move.append(ref)

                # Store ref for verb attachment (use first instance)
                if i == 0:
                    obj_refs[(room_name, name)] = ref
                    print(f"    {ref}: {name}", file=sys.stderr)

        # Move all objects to room
        for ref in refs_to_move:
            move_to_room(moo, ref, room_hash_name)

    return obj_refs


def build_npcs(moo, env, run_hash, use_hash, room_map):
    """Create all NPCs and move to rooms."""
    npcs = env.get("npcs", [])
    parent = env["metadata"].get("npc_parent", "$player")
    npc_refs = {}

    if not npcs:
        return npc_refs

    print("  Creating NPCs:", file=sys.stderr)

    for npc_spec in npcs:
        name = npc_spec["name"]
        hash_name = add_hash_suffix(name, run_hash, use_hash)
        desc = npc_spec.get("description", "")
        aliases = npc_spec.get("aliases", [])
        room = npc_spec.get("room")

        ref = create(moo, hash_name, parent)

        if not ref:
            continue

        if desc:
            describe(moo, ref, desc)
        if aliases:
            add_aliases(moo, ref, aliases)
        if room:
            room_hash_name = room_map.get(room, room)
            move_to_room(moo, ref, room_hash_name)

        npc_refs[name] = ref
        print(f"    {ref}: {name}", file=sys.stderr)

    return npc_refs


def build_verbs(moo, env, run_hash, use_hash, obj_refs, npc_refs, room_map):
    """Attach verbs to objects/NPCs."""
    verbs = env.get("verbs", [])

    if not verbs:
        return

    print("  Attaching verbs:", file=sys.stderr)

    for verb_spec in verbs:
        verb_name = verb_spec["verb"]
        obj_name = verb_spec["object"]
        room_name = verb_spec.get("room")
        code = verb_spec["code"]

        # Resolve object reference
        obj_ref = None

        if room_name:
            # Use room context for disambiguation
            obj_ref = obj_refs.get((room_name, obj_name))
            if not obj_ref:
                # Try NPCs
                obj_ref = npc_refs.get(obj_name)
        else:
            # Search all rooms for object
            for (_, n), ref in obj_refs.items():
                if n == obj_name:
                    obj_ref = ref
                    break
            if not obj_ref:
                obj_ref = npc_refs.get(obj_name)

        # Also check if it's a room name
        if not obj_ref and obj_name in room_map:
            obj_ref = f'"{room_map[obj_name]}"'

        if not obj_ref:
            print(f"    WARNING: Could not resolve object '{obj_name}' for verb '{verb_name}'", file=sys.stderr)
            continue

        set_verb(moo, verb_name, obj_ref, code)
        print(f"    {verb_name} on {obj_ref}", file=sys.stderr)


def generate_test_verb(env, run_hash, use_hash, room_map):
    """Generate test verb code from environment definition."""
    env_name = env["metadata"]["name"]
    test_name_base = env_name.lower().replace(" ", "-").replace("'", "")

    # Test verb name includes hash if enabled
    if use_hash and run_hash:
        test_name = f"test-{test_name_base}-{run_hash}"
    else:
        test_name = f"test-{test_name_base}"

    # Auto-generate test expectations from YAML structure
    test_spec = env.get("test", {})
    rooms = test_spec.get("rooms", [r["name"] for r in env.get("rooms", [])])
    objects = test_spec.get("objects", {})
    npcs = test_spec.get("npcs", [npc["name"] for npc in env.get("npcs", [])])
    verbs = test_spec.get("verbs", [])

    # Generate code using simplified template (no nested functions)
    code_parts = [
        "from moo.sdk import lookup, NoSuchObjectError, NoSuchVerbError",
        "",
        "passed = 0",
        "failed = 0",
        "",
        'print("[bold]--- Rooms ---[/bold]")',
        "rooms = {}",
    ]

    # Room checks
    for room_name in rooms:
        hash_name = add_hash_suffix(room_name, run_hash, use_hash)
        escaped_hash_name = hash_name.replace('"', '\\"')
        code_parts.append("try:")
        code_parts.append(f'    rooms["{room_name}"] = lookup("{escaped_hash_name}")')
        code_parts.append("    passed += 1")
        code_parts.append(f'    print(f"[green]PASS[/green] {room_name}")')
        code_parts.append("except NoSuchObjectError as e:")
        code_parts.append(f'    rooms["{room_name}"] = None')
        code_parts.append("    failed += 1")
        code_parts.append(f'    print(f"[red]FAIL[/red] {room_name}: {{e}}")')
        code_parts.append("")

    # Object checks
    if objects:
        code_parts.append('print("[bold]--- Objects ---[/bold]")')
        for room_name, obj_list in objects.items():
            code_parts.append(f'if rooms.get("{room_name}"):')
            code_parts.append(f'    names = [o.name for o in rooms["{room_name}"].contents.all()]')
            for obj_name in obj_list:
                code_parts.append(f'    if any("{obj_name}".lower() in n.lower() for n in names):')
                code_parts.append("        passed += 1")
                code_parts.append(f'        print(f"[green]PASS[/green] {room_name}: {obj_name}")')
                code_parts.append("    else:")
                code_parts.append("        failed += 1")
                code_parts.append(f'        print(f"[red]FAIL[/red] {room_name}: {obj_name} (not in {{names}})")')
            code_parts.append("")

    # NPC checks
    if npcs:
        code_parts.append('print("[bold]--- NPCs ---[/bold]")')
        for npc_name in npcs:
            hash_name = add_hash_suffix(npc_name, run_hash, use_hash)
            escaped_hash_name = hash_name.replace('"', '\\"')
            code_parts.append("try:")
            code_parts.append(f'    lookup("{escaped_hash_name}")')
            code_parts.append("    passed += 1")
            code_parts.append(f'    print(f"[green]PASS[/green] {npc_name}")')
            code_parts.append("except NoSuchObjectError as e:")
            code_parts.append("    failed += 1")
            code_parts.append(f'    print(f"[red]FAIL[/red] {npc_name}: {{e}}")')
        code_parts.append("")

    # Verb checks
    if verbs:
        code_parts.append('print("[bold]--- Verbs ---[/bold]")')
        for verb_spec in verbs:
            obj_name = add_hash_suffix(verb_spec["object"], run_hash, use_hash)
            escaped_obj_name = obj_name.replace('"', '\\"')
            verb_name = verb_spec["verb"]
            code_parts.append("try:")
            code_parts.append(f'    obj = lookup("{escaped_obj_name}")')
            code_parts.append(f'    obj.get_verb("{verb_name}")')
            code_parts.append("    passed += 1")
            code_parts.append(f'    print(f"[green]PASS[/green] {obj_name}: {verb_name}")')
            code_parts.append("except NoSuchObjectError as e:")
            code_parts.append("    failed += 1")
            code_parts.append(f'    print(f"[red]FAIL[/red] {obj_name}: {verb_name} (object not found: {{e}})")')
            code_parts.append("except NoSuchVerbError:")
            code_parts.append("    failed += 1")
            code_parts.append(f'    print(f"[red]FAIL[/red] {obj_name}: {verb_name} (verb not found)")')
        code_parts.append("")

    code_parts.extend(
        [
            "total = passed + failed",
            'print(f"[bold]{passed}/{total} checks passed.[/bold]")',
        ]
    )

    return test_name, "\n".join(code_parts)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Build MOO environment from YAML")
    parser.add_argument("yaml_file", help="Path to YAML environment file")
    parser.add_argument("--dry-run", action="store_true", help="Parse YAML but don't connect to MOO")
    parser.add_argument("--no-test", action="store_true", help="Skip creating and running test verb")
    parser.add_argument("--hash", action="store_true", help="Force hash suffix mode (override YAML setting)")
    parser.add_argument("--no-hash", action="store_true", help="Force clean name mode (override YAML setting)")
    parser.add_argument("--host", default="localhost", help="MOO server hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=8022, help="MOO server SSH port (default: 8022)")
    args = parser.parse_args()

    # Load environment
    try:
        env = load_environment(args.yaml_file)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error loading YAML: {e}", file=sys.stderr)
        return 1

    env_name = env["metadata"]["name"]

    # Determine hash mode (metadata default, CLI override)
    use_hash = env["metadata"].get("use_hash_suffix", True)
    if args.hash:
        use_hash = True
    elif args.no_hash:
        use_hash = False

    if args.dry_run:
        print(f"Loaded environment: {env_name}")
        print(f"  Hash mode: {'enabled' if use_hash else 'disabled'}")
        print(f"  Rooms: {len(env.get('rooms', []))}")
        print(f"  Objects: {sum(len(objs) for objs in env.get('objects', {}).values())}")
        print(f"  NPCs: {len(env.get('npcs', []))}")
        print(f"  Verbs: {len(env.get('verbs', []))}")
        return 0

    # Generate hash only if needed
    run_hash = generate_hash() if use_hash else None

    hash_info = f" (run: {run_hash})" if run_hash else ""
    print(f"=== Building {env_name}{hash_info} ===", file=sys.stderr)

    try:
        with MooSSH(host=args.host, port=args.port) as moo:
            moo.enable_automation_mode()

            print("\n--- Phase 1: Rooms and exits ---", file=sys.stderr)
            room_map = build_rooms(moo, env, run_hash, use_hash)

            print("\n--- Phase 2: Objects ---", file=sys.stderr)
            obj_refs = build_objects(moo, env, run_hash, use_hash, room_map)

            print("\n--- Phase 3: NPCs ---", file=sys.stderr)
            npc_refs = build_npcs(moo, env, run_hash, use_hash, room_map)

            print("\n--- Phase 4: Verbs ---", file=sys.stderr)
            build_verbs(moo, env, run_hash, use_hash, obj_refs, npc_refs, room_map)

            if not args.no_test:
                print("\n--- Phase 5: Test verb ---", file=sys.stderr)
                test_name, test_code = generate_test_verb(env, run_hash, use_hash, room_map)
                set_verb(moo, test_name, "$programmer", test_code)

                print(f"\n--- Running {test_name} ---", file=sys.stderr)
                moo.run(test_name)

        print("\n=== Build complete. ===", file=sys.stderr)
        if not args.no_test:
            print(f"Test verb: {test_name}", file=sys.stderr)

        return 0

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n=== Build failed: {e} ===", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
