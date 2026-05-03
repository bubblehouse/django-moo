"""
Sanity checks across every Zork 1 verb file in the bootstrap.

These tests do not exercise verb behavior — they only assert that the static
shape of the generated/hand-written verb files holds:

* Each ``.py`` parses as Python (catches shebang/indentation regressions).
* Each ``.py`` carries a valid ``#!moo verb …`` shebang that DjangoMOO's own
  ``parse_shebang`` helper accepts.

The deferred verb-translation regeneration session benefits from this CI
safety net: a translator change that breaks the shebang grammar shows up
here before any runtime test does.
"""

from __future__ import annotations

import ast
import importlib.resources
from pathlib import Path

import pytest

from moo.bootstrap import parse_shebang


def _verb_files() -> list[Path]:
    """Return every .py under moo/bootstrap/zork1/verbs/."""
    pkg = importlib.resources.files("moo.bootstrap.zork1") / "verbs"
    files: list[Path] = []
    with importlib.resources.as_file(pkg) as root:
        for path in Path(root).rglob("*.py"):
            # Skip __init__.py (no shebang).
            if path.name == "__init__.py":
                continue
            files.append(path)
    return files


VERB_FILES = _verb_files()


@pytest.mark.parametrize("path", VERB_FILES, ids=lambda p: p.relative_to(p.parents[2]).as_posix())
def test_verb_file_parses_as_python(path: Path):
    """Each verb file is valid Python source."""
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))


@pytest.mark.parametrize("path", VERB_FILES, ids=lambda p: p.relative_to(p.parents[2]).as_posix())
def test_verb_file_has_valid_shebang(path: Path):
    """Each verb file's first line is a parse_shebang-accepted ``#!moo verb …``."""
    source = path.read_text(encoding="utf-8")
    result = parse_shebang(source)
    assert result is not None, f"{path.name}: shebang did not parse"
    names, on, _dspec, _ispec = result
    assert names, f"{path.name}: shebang declared no verb names"
    assert on, f"{path.name}: shebang missing --on target"
