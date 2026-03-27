---
name: tech-librarian
description: Sync documentation across the three layers in django-moo — Sphinx guides, AI skill files, and AGENTS.md. Use when asked to do a doc pass, audit documentation drift, update Sphinx to match recent changes, or keep the layers consistent.
compatibility: Designed for Claude Code. Requires access to the django-moo repository and git history.
---

# Tech Librarian

This skill guides a documentation sync pass across the three layers in django-moo. When new features land or bugs get fixed, the knowledge lands in whichever layer prompted the fix first. The others drift. A sync pass finds the gaps and closes them.

See [layers.md](references/layers.md) for the canonical file list for each layer and what each covers. See [translation.md](references/translation.md) for audience translation rules when porting content between layers.

## Phase 1: Orient

Start by surveying what has changed since the last sync pass.

```
git log --oneline --since="2 weeks ago"
```

Adjust the `--since` window to cover everything since the last `docs:` commit. Look for:
- `feat:` commits — new features that need documentation in all three layers
- `fix:` commits — bug fixes that may have corrected API assumptions in skills or AGENTS.md
- `docs:` commits — check what was updated and what adjacent areas were left untouched

For each notable commit, ask: which layer did this change land in? Do the others reflect it?

Also check the project memory for recent additions:
```
~/.claude/projects/-Users-philchristensen-Workspace-bubblehouse-django-moo/memory/
```

Memory files often capture gotchas and corrections that have not yet been ported to any documentation layer.

## Phase 2: Gap Detection

Scan the layers for common drift types. Work through this checklist:

**Output mechanisms** — does each layer correctly describe `print()`, `obj.tell()`, and `write()`? These three behave differently and the distinction matters.

**API names** — skill files and AGENTS.md accumulate corrections (`get_pobj_str` not `get_pobj_string`, `obj.parents.all()` not `obj.parents`). Check whether Sphinx reflects the corrected names.

**Return value behavior** — `return "..."` from a verb does not print to the player. All three layers should state this clearly with an example.

**Parser behavior** — preposition synonym groups, verb search order, `--dspec`/`--ispec` nuances. Sphinx guide `10_parser.md` and `11_creating_verbs.md` are most likely to be stale.

**SDK functions** — new functions added to `moo/sdk.py` (e.g. `open_editor`, `open_paginator`, `players()`, `connected_players()`, `set_task_perms()`) need entries in `12_more_verbs.md` and the `verb-author` skill's `references/sdk.md`.

**New verb patterns** — any new verb added to `moo/bootstrap/default_verbs/` that introduces a pattern not already documented (property access, object creation, permission checks).

**Sandbox restrictions** — new `ALLOWED_MODULES`, new `BLOCKED_IMPORTS`, or new guard mechanisms belong in `09_sandbox_security.md` and the `sandbox-auditor` skill.

**New object classes** — `$furniture`, `$container`, `$note` additions need coverage in `game-designer` skill and potentially `04_objects.md`.

**Sphinx toctree** — any new guide page not referenced in a `toctree` directive is orphaned and generates a build warning. Confirm new files are included in `docs/source/index.rst` or the relevant toctree.

## Phase 3: Port

For each gap found in Phase 2, port the content to the missing layer.

**Direction: Skills/AGENTS.md → Sphinx**

Skills and AGENTS.md tend to be ahead. When porting to Sphinx:
- Translate for human readers (see [translation.md](references/translation.md))
- Add "why it matters" context, not just the rule
- Anchor the content to a realistic verb scenario
- Remove AI agent workflow instructions entirely

**Direction: Sphinx → Skills/AGENTS.md**

Less common. When Sphinx gets a major structural update, check whether skills need the same fact in terse form. If a Sphinx section corrects a common mistake, add a decision rule to the relevant skill.

**Direction: Memory → All Layers**

Memory files capture ephemeral investigations. If a memory file contains a stable fact (an API name, a gotcha, a behavioral rule), that fact belongs in at least one documentation layer. Port it and leave the memory as a pointer.

For each change, make one commit per destination layer:
```
docs: update 11_creating_verbs.md with correct output mechanism names
docs: update verb-author skill with $furniture pattern
```

## Phase 4: Verify

After porting, confirm consistency:

1. Pick two or three recently corrected facts (e.g. `return "..."` not printing, `obj.parents.all()` requirement).
2. Find each fact in all three layers that should cover it.
3. If any layer still has the wrong version, fix it now.

Then validate the Sphinx build:

```
uv run sphinx-build -b dummy -W docs/source docs/_build/dummy
uv run sphinx-lint docs/source/
```

The dummy builder validates all cross-references and toctree entries. `sphinx-lint` catches RST/MyST style issues. Both must pass clean before committing doc changes.

**Known pre-existing build failure:** `sphinx_autodoc_typehints` emits unresolvable-forward-reference warnings for asyncssh's `SSHReader` type (inherited methods on `moo.shell.server.SSHServer`). These cannot be suppressed via `suppress_warnings` because the extension uses Python's logging system directly, bypassing Sphinx's warning infrastructure. Ignore them — they are not caused by doc changes and were present before the Diátaxis reorganisation.

**`sphinx-lint` path:** guide pages now live under `docs/source/` in Diátaxis subdirectories (`explanation/`, `how-to/`, `reference/`, `tutorials/`), not `docs/source/guide/`. Pass `docs/source/` as the root.

Update the project memory sync record:
```
~/.claude/projects/-Users-philchristensen-Workspace-bubblehouse-django-moo/memory/project_doc_sync_pattern.md
```

Add a note of what was synced and the date, so the next pass knows where to start.

## Reference Files

- [layers.md](references/layers.md) — canonical file list for each layer, scope boundaries, and how to read each
- [translation.md](references/translation.md) — audience translation rules for porting between layers
