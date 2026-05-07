"""CLI entry point — see :doc:`/reference/zil-importer`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .converter import extract_all
from .generator import generate_all
from .parser import parse_file


def _expand_manifest(zil_files: list[str]) -> list[str]:
    """Resolve any ``<INSERT-FILE …>`` directives in the input files.

    A "manifest" is a top-level ZIL file (e.g. ``zork1.zil``) whose body is
    almost entirely ``<INSERT-FILE "…">`` forms.  Real source files don't
    have any.  Returns the flattened, in-order list of real source files —
    manifests themselves are dropped because they carry no game content the
    importer consumes today.
    """
    seen: set[str] = set()
    out: list[str] = []

    def visit(zil_path: str) -> None:
        zil_path = str(Path(zil_path).resolve())
        if zil_path in seen:
            return
        seen.add(zil_path)
        nodes, _src = parse_file(zil_path)
        base = Path(zil_path).parent
        inserts = [
            str(node[1]) for node in nodes if isinstance(node, list) and len(node) == 2 and node[0] == "INSERT-FILE"
        ]
        # Always include the file itself.  Manifests like ``zork1.zil`` carry
        # top-level ``<SETG …>`` forms (e.g. ``<SETG ZORK-NUMBER 1>``) that
        # initialise zstate slots — dropping them silently disables every
        # ZORK-NUMBER == 1 branch in translated routines.
        out.append(zil_path)
        for rel in inserts:
            target = base / (rel if rel.endswith(".zil") else rel + ".zil")
            visit(str(target))

    for zil in zil_files:
        visit(zil)
    return out


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
    parser.add_argument(
        "--lint",
        action="store_true",
        help=(
            "After generating, run pylint on the output directory and fail "
            "the import if the score drops below --lint-threshold.  "
            "Off by default — pylint takes ~15s on the full Zork 1 bootstrap."
        ),
    )
    parser.add_argument(
        "--lint-threshold",
        type=float,
        default=9.0,
        metavar="SCORE",
        help="Minimum acceptable pylint score (0-10, default 9.0).  Only used with --lint.",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve any <INSERT-FILE …> manifests (e.g. zork1.zil) into the flat
    # list of source files to actually parse.  Real source files pass
    # through unchanged.
    try:
        source_files = _expand_manifest(args.zil_files)
    except (OSError, SyntaxError, ValueError) as exc:
        log.error("Failed to expand manifest: %s", exc)
        return 1
    log.info("Manifest expanded to %d files", len(source_files))

    # Parse all ZIL files and merge their AST nodes
    all_nodes = []
    for path in source_files:
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
    rooms, objects, routines, tables, globals_dict, syntax_dict, synonyms_dict = extract_all(all_nodes)
    log.info("  Rooms:    %d", len(rooms))
    log.info("  Objects:  %d", len(objects))
    log.info("  Routines: %d", len(routines))
    log.info("  Tables:   %d", len(tables))
    log.info("  Globals:  %d", len(globals_dict))
    log.info("  Syntax:   %d", len(syntax_dict))
    log.info("  Synonyms: %d", len(synonyms_dict))

    if not rooms and not objects:
        log.error("No rooms or objects found — check your input files.")
        return 1

    # Generate bootstrap
    output_dir = Path(args.output)
    log.info("Generating bootstrap at %s ...", output_dir)

    # Optional per-file pylint validation.  Off by default — pylint's
    # warmup is ~0.8s and warm calls are ~0.04-0.1s per file, so opting
    # in adds 30-60s to a regen.  When on, the generator raises
    # immediately as soon as a generated file falls below the score
    # threshold so the operator sees the offending file's findings
    # instead of hunting through a post-hoc full report.
    linter = None
    if args.lint:
        from .lint import Linter  # pylint: disable=import-outside-toplevel

        log.info("Per-file pylint enabled (threshold %.2f)", args.lint_threshold)
        linter = Linter(threshold=args.lint_threshold)

    try:
        generate_all(  # pylint: disable=unexpected-keyword-arg
            rooms,
            objects,
            routines,
            output_dir,
            tables={name: t.values for name, t in tables.items()},
            globals_dict=globals_dict,
            syntax_dict=syntax_dict,
            synonyms_dict=synonyms_dict,
            linter=linter,
        )
    except RuntimeError as exc:
        log.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
