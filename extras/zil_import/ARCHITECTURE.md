# ZIL Importer Architecture

This document records the known mismatches between ZIL semantics and
DjangoMOO's verb/object/parser model, and the rules that govern how the
importer evolves toward DjangoMOO idioms over time. Read this before
adding code to `extras/zil_import/` or proposing changes to
`moo/core/parse.py` / `moo/sdk/`.

The full review that produced this document lives in
`~/.claude/plans/we-re-in-the-midst-tender-fiddle.md`.

## The hard rules

1. **Never modify `moo/core/parse.py`** to support a translator gap. The
   parser already has `do_command` (pre-dispatch hook at lines 68-76) and
   `turnfunc` (post-dispatch hook at lines 87-95). If those don't fit the
   need, the translator's design is wrong, not the parser.

2. **Never add a new function to `moo/sdk/`** to support a translator gap.
   `moo/sdk/` is the verb-author public API. Translation-specific helpers go
   in `extras/zil_import/verbs/zil_sdk/`.

3. **Every translator change should shrink
   `extras/zil_import/verbs/zil_sdk/` and
   `moo/bootstrap/zork1/verbs/_global/substrate_*/`, not grow them.** If a
   fix grows them, escalate before landing — it's likely re-implementing
   something DjangoMOO already does. Quarantine workarounds for broken
   Z-machine primitives are fine but should be tagged as temporary in a
   comment.

4. **No more god-verbs in new translator output.** Each generated verb file
   is one verb name (or a tight synonym group) on one object class — not a
   30-name shebang with `if player_verb in [...]` switches. ZIL
   OBJECT-FUNCTION blocks should decompose into per-verb files, each able
   to `passthrough()` for substrate fallthrough.

## The mismatches

### 1. zork1 is its own self-contained bootstrap

The zork1 bootstrap does not share a class hierarchy with `default/`. It
builds its own root classes (`$zork_root`, `$zork_thing`, `$zork_room`,
`$zork_exit`) and substrate verbs. That's correct — Zork is a single-game
dataset.

Refactoring goal: **adopt DjangoMOO mechanisms where they actually
simplify the ZIL translation; leave Zork-specific shapes alone where they
don't.** Some Z-machine concepts (function-exits, conditional-exits,
door-exits, M-BEG gating on direction tokens) may not fit cleanly into a
`$exit`-style verb chain — and forcing them to is the same mistake as
recreating Z-machine parser internals in DjangoMOO. The win is reduced
*unnecessary* indirection, not stylistic conformity.

### 2. `do_command` and `turnfunc` exist already

`moo/core/parse.py:68-76` runs the System Object's `do_command` verb
before normal dispatch; truthy return short-circuits dispatch. Lines
87-95 fire `turnfunc` on the player's room after every command.

In ZIL terms: `do_command` ≈ M-BEG dispatch site, `turnfunc` ≈ M-END.
The translator emits `preturnfunc` (M-BEG) and `turnfunc` (M-END) verbs
on rooms/objects, and a `verbs/system/do_command.py` template that
forwards to `preturnfunc` on the player's location (and on the
underlying physical room when the location is a vehicle).

### 3. `run_v_routine` is a workaround, not a feature

`extras/zil_import/verbs/zil_sdk/dispatch.py` implements
`run_v_routine(verb)` which prepends `v-` and invokes the verb on
`$zork_thing`. This is a workaround for ZIL's
"ACTION-routine-then-V-verb" cascade, which DjangoMOO already provides
natively via verb inheritance + `passthrough()`.

Phase 3 plan: object-specific ACTIONs become per-verb files calling
`passthrough()`, substrate verbs lose the `v-` prefix, and `run_v_routine`
shrinks to nothing.

There is one known quarantine inside `run_v_routine`: the
`WALK_VERBS` short-circuit routes movement verbs (walk/go/move/run/
proceed/step) to `_.zil_sdk.walk()` instead of falling through to the
broken substrate `v-walk` (which uses Z-machine exit-table primitives).
This is documented in `dispatch.py` and stays until Phase 3 lands a
verb-driven exit model.

### 4. Z-machine primitives leaked through

The translator is currently leaving Z-machine names in generated code.
Some are dead (no Python definition exists; the code crashes when
called); others are stored as global state on `$zil_sdk` which is
indirected and slow.

Authoritative inventory: see
`extras/zil_import/tests/test_no_zmachine_leakage.py:_KNOWN_PRIMITIVE_LEAKS`.
That allowlist is the canonical record of leak sites; this table summarizes
counts by primitive as of 2026-05-03.

| Primitive | Total occurrences | Definition? |
|-----------|-------------------|-------------|
| `getpt`   | 15                | none — crashes at runtime |
| `ptsize`  | 11                | none — crashes at runtime |
| `UEXIT` / `NEXIT` / `FEXIT` / `CEXIT` / `DEXIT` | 15 | as zstate keys; semantically wrong |
| `P-LEXV`  | 74                | as zstate; raw lex-vector access |
| `P-PRSO` / `P-PRSI` | 33      | as zstate; should be `context.parser.get_dobj/iobj` |
| `PRSA`    | 4                 | should be `verb_name` |
| `M-BEG` / `M-LOOK` / `M-END` / `M-ENTER` | 187 | string-compared as `rarg`; lifecycle leakage |
| `WINNER`  | 12                | mostly mapped to `context.player`; some leakage |

The allowlist test (`test_no_new_zmachine_primitive_leakage`) catches new
leakage in files that don't currently leak. The companion
`test_allowlist_does_not_grow_stale` fires when a Phase 3 cleanup makes
an allowlist entry obsolete, prompting removal.

Phase 3 cleanup priority: each primitive's call sites get one of
(i) replace with native DjangoMOO equivalent, (ii) implement in
`zil_sdk` if genuinely missing, (iii) skip the generated path entirely
because it's redundant.

### 5. Pre-action verbs (partial Phase 3 done 2026-05-03)

`_global/substrate_pre/{pre_take, pre_drop, pre_put, pre_fill, pre_burn,
pre_read, pre_sgive, pre_turn, pre_mung, pre_board, pre_give, pre_move}.py`
register verbs named `pre-take`, `pre-drop`, etc. on `$zork_thing`.

**Status:** as of 2026-05-03 the syntax-dispatch layer in
`extras/zil_import/generator.py` now invokes `pre-<verb>` before
`v-<verb>` and short-circuits on truthy return. The pre-verbs are no
longer dead. Smoke test + 2662-test broader suite pass.

**Remaining Phase 3 work for this item:** pre-checks move into the body
of the `take` / `drop` / `put` etc. verb on a Zork class, followed by
`passthrough()`. Drops the separate `pre-` verb registration step
entirely. Lower priority now that the wiring is correct.

### 6. God-verbs with `player_verb in [...]` switches

ZIL OBJECT-FUNCTION blocks become single verb files with 30+ verb names
in the shebang and `if player_verb in [...]` switches in the body. This
is correct ZIL semantics but bypasses DjangoMOO's natural verb dispatch.

Phase 3: decompose. Each verb name in the shebang becomes its own file.

### 7. Atom registry on the System Object (partial Phase 3 done 2026-05-03)

**Status:** as of 2026-05-03 the translator emits `lookup("atom")` for
runtime atom resolution. Each room/object gets the atom-form (lower-snake)
as an `add_alias(...)` call at bootstrap time so `lookup` matches them.

The System Object property registry (`_.set_property("rope", obj)`) is
kept *for bootstrap-time use only* — `--on $atom` shebangs still resolve
through `system.get_property(name=on[1:])` in
`moo/bootstrap/__init__.py:220`. Removing the registry broke 79 verb
files at load time during the test suite; restoring it kept that path
intact while leaving the runtime migration in place.

The auto-import scan in the translator now also scans param/aux default
expressions (it previously only scanned the body), catching cases where
`lookup("foo")` lives in a default value rather than in the body proper.

**Remaining Phase 3 work for this item:** make `--on $atom` shebangs
resolve via alias instead of System Object property, then drop the
registry entirely. That's a `moo/bootstrap/__init__.py` change — out of
scope of the no-core-changes hard rule (it's the bootstrap loader, not
the parser or SDK), but worth a design conversation before doing it.

### 8. Direction tokens stored as zstate atoms

`_.zil_sdk.zstate_get("P?NORTH")`, `P?LAND`, `P?EAST` etc. — direction
atoms stored on `$zil_sdk` as if they were game state. They should be
plain Python strings compared against `context.parser.get_dobj_str()`.

Phase 3: translator emits string literals instead of zstate lookups for
P? direction atoms.

## RestrictedPython gotchas to remember when writing zil_sdk templates

The ZIL importer's helper templates run under RestrictedPython. Names
starting with `_` are rejected at compile time. This applies to:

- Module-level constants: use `WALK_VERBS` not `_WALK_VERBS`
- Local variables: `vehicle` not `_vehicle`, `here_room` not `_here`
- Helper function names defined inside a verb: same rule

Verb files declare verb names in the `#!moo verb …` shebang. If a verb
file has internal `verb_name == "X"` dispatch, every X must appear in
the shebang or `_.zil_sdk.X(...)` will fail with `AttributeError: ZIL
SDK has no attribute 'X'`.

## File layout

```
extras/zil_import/
├── ARCHITECTURE.md          ← this file
├── PHASE_E4E_PLAN.md        ← in-progress Zork 1 smoke-test extension
├── parser.py                ← ZIL → AST
├── converter.py             ← AST → IR (rooms/objects/routines)
├── ir.py                    ← IR dataclasses
├── translator.py            ← IR → Python verb bodies (statement/expr translation)
├── generator.py             ← assembles bootstrap dirs and emits classes/rooms/objects/exits/tables
├── cli.py / __main__.py     ← entry point: `uv run python -m extras.zil_import …`
├── verbs/                   ← templates copied verbatim into output
│   ├── PREFIX.py / SUFFIX.py
│   ├── system/
│   │   └── do_command.py    ← System Object pre-dispatch hook for preturnfunc
│   └── zil_sdk/             ← ZIL→DjangoMOO impedance shims
│       ├── dispatch.py
│       ├── death.py
│       ├── flags.py
│       ├── movement.py
│       ├── output.py
│       ├── queue_sdk.py
│       ├── random_sdk.py
│       ├── score.py
│       └── state.py
└── tests/
    └── test_no_zmachine_leakage.py   ← regression test (next)
```
