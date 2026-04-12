"""
CLI entry point for the ZIL → DjangoMOO bootstrap converter.

Usage:
    uv run python -m extras.zork_import dungeon.zil [actions.zil ...] --output moo/bootstrap/zork1
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .converter import extract_all
from .generator import generate_all
from .parser import parse_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Infocom ZIL source files to a DjangoMOO bootstrap package.",
    )
    parser.add_argument(
        "zil_files",
        nargs="+",
        metavar="FILE.zil",
        help="One or more ZIL source files to parse (dungeon.zil first, then actions.zil).",
    )
    parser.add_argument(
        "--output",
        default="moo/bootstrap/zork1",
        metavar="DIR",
        help="Output directory for the generated bootstrap package (default: moo/bootstrap/zork1).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse all ZIL files and merge their AST nodes
    all_nodes = []
    for path in args.zil_files:
        log.info("Parsing %s ...", path)
        try:
            nodes, _source = parse_file(path)
            all_nodes.extend(nodes)
            log.info("  → %d top-level forms", len(nodes))
        except (OSError, SyntaxError, ValueError) as exc:
            log.error("Failed to parse %s: %s", path, exc)
            return 1

    # Extract IR
    log.info("Extracting world model ...")
    rooms, objects, routines, tables = extract_all(all_nodes)
    log.info("  Rooms:    %d", len(rooms))
    log.info("  Objects:  %d", len(objects))
    log.info("  Routines: %d", len(routines))
    log.info("  Tables:   %d", len(tables))

    if not rooms and not objects:
        log.error("No rooms or objects found — check your input files.")
        return 1

    # Generate bootstrap
    output_dir = Path(args.output)
    log.info("Generating bootstrap at %s ...", output_dir)
    generate_all(  # pylint: disable=unexpected-keyword-arg
        rooms, objects, routines, output_dir, tables={name: t.values for name, t in tables.items()}
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
