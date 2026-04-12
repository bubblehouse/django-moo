#!/usr/bin/env python3
"""
moo_scatter.py - Redistribute loose objects from one room to random rooms.

Uses @divine location to select destinations, then @eval to move each object
directly via the ORM (bypassing $furniture moveto restrictions).

Usage:
    python moo_scatter.py                        # scatter Agency objects
    python moo_scatter.py --source "#23"         # scatter from a specific room #N
    python moo_scatter.py --objects "#79 #80"    # scatter specific objects only
    python moo_scatter.py --dry-run              # show plan without moving anything
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from moo_ssh import MooSSH  # pylint: disable=wrong-import-position

# Rooms to never use as scatter destinations
SKIP_ROOMS = {
    "The Agency",
    "The Laboratory",
    "The Neighborhood",
    "Mail Distribution Center",
    "Generic Room",
}


def divine_rooms(moo):
    """Call @divine location and return list of (name, #N) tuples."""
    raw = moo.run("@divine location")
    rooms = []
    for line in raw.splitlines():
        # Matches: "  some room name (#42)"
        m = re.match(r"\s*(.*?)\s+\(#(\d+)\)\s*$", line)
        if m:
            name, pk = m.group(1).strip(), m.group(2)
            if name not in SKIP_ROOMS:
                rooms.append((name, f"#{pk}"))
    return rooms


def survey_room(moo, room_ref):
    """Return survey output for a room ref (#N or name)."""
    return moo.run(f"@survey {room_ref}")


def parse_contents(survey_output):
    """Extract (name, #N) pairs from @survey Contents section."""
    objects = []
    in_contents = False
    for line in survey_output.splitlines():
        if "Contents:" in line:
            in_contents = True
            continue
        if in_contents:
            if line.startswith("  ") or line.startswith("\t"):
                m = re.match(r"\s+(.*?)\s+\(#(\d+)\)\s*$", line)
                if m:
                    objects.append((m.group(1).strip(), f"#{m.group(2)}"))
            else:
                break
    return objects


def move_object(moo, obj_pk, dest_pk, dry_run=False):
    """Move object to destination using direct ORM assignment (bypasses moveto)."""
    obj_num = obj_pk.lstrip("#")
    dest_num = dest_pk.lstrip("#")
    cmd = f'@eval "obj = lookup({obj_num}); dest = lookup({dest_num}); obj.location = dest; obj.save()"'
    if dry_run:
        print(f"    [dry-run] {cmd}")
        return "(dry-run)"
    return moo.run(cmd)


def main():
    parser = argparse.ArgumentParser(description="Scatter objects from a source room to random rooms via @divine.")
    parser.add_argument("--source", default="#23", help="Source room #N (default: #23 The Agency)")
    parser.add_argument("--objects", default="", help="Space-separated #N IDs to scatter (default: all non-agent contents)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without moving anything")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8022)
    args = parser.parse_args()

    # Agent/coordination object IDs to always skip
    # (players, The Dispatch Board, The Survey Book, Agent of the Moment)
    SKIP_IDS = {
        "#5",   # Wizard
        "#25",  # Mason
        "#26",  # Tinker
        "#27",  # Joiner
        "#28",  # Harbinger
        "#29",  # Stocker
        "#30",  # Foreman
        "#311", # Warden
        "#312", # Archivist
        "#313", # Tailor
        "#360", # The Dispatch Board
        "#361", # The Survey Book
        "#363", # Agent of the Moment
    }
    # Add any inspector/neighbour/wanderer agents that might be home
    SKIP_CLASSES = {"$player"}  # names starting with capitals are agents

    with MooSSH(host=args.host, port=args.port) as moo:
        moo.enable_automation_mode()

        # Survey the source room
        print(f"Surveying source room {args.source}...")
        survey = survey_room(moo, args.source)
        print(survey)
        print("---")

        if args.objects:
            # Caller specified exact objects
            to_scatter = [(f"obj {pk}", pk) for pk in args.objects.split()]
        else:
            contents = parse_contents(survey)
            # Filter out agents and coordination objects
            to_scatter = [
                (name, pk) for name, pk in contents
                if pk not in SKIP_IDS and not name[0].isupper()
            ]

        if not to_scatter:
            print("Nothing to scatter.")
            return

        print(f"Objects to scatter ({len(to_scatter)}):")
        for name, pk in to_scatter:
            print(f"  {name} ({pk})")
        print("---")

        # Divine destination rooms
        print("Consulting the aether for destinations...")
        rooms = divine_rooms(moo)
        if not rooms:
            # Try once more — the sample is random, so a retry is reasonable
            print("No usable rooms on first divine — trying again...")
            rooms = divine_rooms(moo)
        if not rooms:
            print("ERROR: @divine location returned no usable rooms.")
            sys.exit(1)

        print(f"Destinations ({len(rooms)}):")
        for name, pk in rooms:
            print(f"  {name} ({pk})")
        print("---")

        # Distribute round-robin
        print("Moving objects...")
        for i, (obj_name, obj_pk) in enumerate(to_scatter):
            dest_name, dest_pk = rooms[i % len(rooms)]
            result = move_object(moo, obj_pk, dest_pk, dry_run=args.dry_run)
            print(f"  {obj_name} ({obj_pk}) -> {dest_name} ({dest_pk}): {result.strip()}")

        # Verify source room is clear
        print("\nSource room after scatter:")
        print(survey_room(moo, args.source))


if __name__ == "__main__":
    main()
