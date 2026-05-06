# ZIL Importer — current state and remaining work (2026-05-05)

Snapshot after the SDK relocation refactor and the Phase E-4-e treasure
extension. Pair with `ARCHITECTURE.md` (design rules), `PHASE_E4E_PLAN.md`
(per-treasure walkthrough), and `PHASE_3_BACKLOG.md` (translator-side
refactor items).

## Where we are

**Smoke test** (`extras/zil_import/scripts/zork1_smoke.py`):

- Reproducible score **108 / 350** across consecutive runs, rank
  "Junior Adventurer", clean PASS in ~70s.
- One-shot score of 254 was observed immediately after a fresh
  full-verb purge + re-sync, but did not reproduce — likely an
  artifact of accumulated trophy-case / room-discovered state, not a
  real baseline.  See category A.3 below.
- All 19 canonical Zork 1 treasures collected at least once during the run.
- 17 of them deposited in the trophy case; 2 (emerald, scarab) taken
  during the Sandy Beach excursion which is a one-way trip and so do not
  reach the case.
- Three treasures that previously needed bespoke workarounds now go
  through their canonical solutions: trident (Atlantis swap), skull
  (LLD bell-book-candles ritual), bauble (canary winding).

**Translator state:**

- SDK verbs relocated from a synthetic `$zil_sdk` object to the System
  Object, `$zork_root`, and `$player`. Translated routines now read as
  `obj.flag(...)`, `obj.set_flag(...)`, `obj.getp(...)`, `obj.desc()`,
  `obj.moveto(dest)`, `context.player.zstate_get(...)` etc.
- Generated verbs hoist `parser = context.parser` and `player =
  context.player` when used 2+ times, cache repeated `lookup("X")`
  calls, prefer `this` over `lookup("<owner>")`, and emit `obj.foo()`
  in place of `obj.invoke_verb("foo")` when the verb name is a Python
  identifier.
- `obvious` is wired through the intrinsic Object field in both flag
  reads/writes and 030_objects.py emission (no more divergent Property
  records).
- ZIL objects with the same DESC (e.g. MIRROR-1 / MIRROR-2) are kept as
  separate Django Objects via `"<desc> (<atom>)"` disambiguation —
  matches the rule that already covers same-DESC rooms (FOREST-1/2/3).

## Remaining work, by category

### A. Score gap (108 → 350)

Each item below is a concrete +N score increment that today's smoke
leaves on the table.

1. **Deposit emerald + scarab.** They are picked up at the end of the
   boat run but the smoke exits at Sandy Beach without returning to
   the trophy case. The river system is one-way; reaching Living Room
   from Sandy Beach is `path → ... → Forest Path → ...` overland,
   ~10–12 commands. Worth ≈ +25 (TVALUE 15 + first-pickup VALUE).
2. **Land-of-the-Dead room-discovery score.** Entering a new room
   awards points the first time. The LLD detour visits ~12 rooms
   that earlier smokes never reached; some of those increments
   probably aren't firing because of state carried between runs.
3. **Score variance between runs.** Successive smokes can vary by
   ±10–20. Suspected cause: trophy-case state plus `score-obj`
   (one-shot first-pickup bonus) interaction across runs. Reset
   snippet should also push existing trophy-case contents back to
   their canonical home rooms before each run; today's reset only
   touches a subset.
4. **Endgame and bonus paths.** Master Adventurer (350) requires
   the post-treasure endgame. Out of scope for the importer, listed
   here for completeness.

### B. Bar recovery is fragile

The trident detour parks the platinum bar at Atlantis. The smoke
recovers it later by going back to Mirror Room 2 and rubbing the
mirror a second time. This works **only if the database has both
`MIRROR-1` and `MIRROR-2` as distinct Objects** — which the new
`<desc> (<atom>)` disambiguation in `_gen_objects` ensures on a clean
sync, but the smoke can still pick up the wrong mirror if a stale
single-object mirror remains from an older run.

Mitigation: the smoke's reset snippet now resolves `mirror_1` /
`mirror_2` by alias and pins them back to MR1 / MR2 every run; if a
legacy "name = mirror" Object lingers from before the dedup fix, both
aliases collapse onto it and the swap silently breaks.

**Concrete next step:** add a startup assertion in the reset snippet
that fails loudly when fewer than two distinct mirror Objects are
found, instead of silently picking the first one.

### C. Stale-verb sweep on the bootstrap loader

Discovered while debugging the bauble. `bootstrap.load_verbs` only
prunes Verb rows whose source file no longer exists on disk. When a
verb file's *shebang* changes (e.g. moves from `--on $canary` to
`--on $broken_canary`), `add_verb(replace=True)` only replaces the
verb on the new origin — the stale Verb row on the old origin stays,
its filename still resolves to a real file, and the parser may
dispatch to it instead of the new file.

Concrete fix: extend `_remove_stale_repo_verbs` (or `add_verb`) to
also drop existing Verb rows that share a filename but have a
different origin than the current shebang resolves to.

Today's smoke works around this by purging all Verb rows for the
zork1 repo before re-syncing, but that's a manual step the operator
has to remember.

### D. Translator polish (carry-overs from `PHASE_3_BACKLOG.md`)

These items still apply post-relocation. Touching them should keep
shrinking the size of the generated `_global/substrate_*` and the
zil_sdk shims.

1. **God-verb decomposition** (Backlog item 1). Object-function blocks
   like `iboat_function.py` still emit a single 30-name shebang with
   `if player_verb in [...]` switches. Splitting into per-verb files
   would let the parser do natural dispatch and remove the
   `run_v_routine` fallthrough chain.
2. **Per-exit-type evaluation** (Backlog item 2). UEXIT/NEXIT could
   live as `$zork_exit` verbs the way `default/verbs/exit/move.py`
   does; FEXIT/CEXIT/DEXIT keep their data-driven form.
3. **Drop `v-` prefix on substrate verbs** (Backlog item 3).
   `passthrough()` covers ZIL's "ACTION then V-verb" cascade once the
   substrate verb registers under the natural name.
4. **Skip parser-internal routines** (Backlog item 4). `syntax_check`,
   `clause`, `many_check`, etc. only run from ZIL entry points
   DjangoMOO bypasses; skipping them removes ~50% of the remaining
   primitive leakage in one pass.

### E. Predicate dispatch

The translator now emits `_.zork_thing.invoke_verb("forest-room?")`
for `<FOREST-ROOM?>`-style predicate calls (the `?` suffix can't go
through Python attribute access). `_verb_attr_safe` already gates the
non-predicate path; predicates are a separate call site that just
fixed. Sweep through the rest of the translator for similar patterns
that might still emit bare `foo_p()`.

### F. Z-machine primitive leakage

`tests/test_no_zmachine_leakage.py` ratchets the count of
`getpt`/`ptsize`/`UEXIT`/`PRSA`/etc. references. Current baseline is
**51**. Items D.2 (per-exit-type) and D.4 (skip parser-internals)
together would bring this close to zero.

### G. Bauble path is a shortcut

Today the smoke pre-sets `egg.open = True` at reset time so the
unbroken canary is reachable without going through `BAD-EGG`. The
canonical path is the thief opening the egg in his treasure room
(`thief_in_treasure.py` / `otval_frob.py`). Driving that from the
smoke needs the thief AI cycle to be reproducible enough to wait for
the steal → walk → open sequence. Realistic next step: write a
separate scenario test that runs many turns, asserts EGG is OPENBIT,
then takes the canary back.

## Reset gaps the smoke should backfill

Roughly in priority order:

- Trophy-case contents → original home rooms before each run (B-3).
- All cyclic / shared objects beyond the mirror dedup (A-2 cascades
  from this).
- Daemon queue + counter is reset; verify no carry-over of
  `XB`/`XC`/`HOT-BELL` once the LLD ritual fires more than once.

## Files / next-touch targets

| Concern | File(s) |
|---------|---------|
| God-verb split | `extras/zil_import/translator.py` (`translate`, `translate_m_clause`) |
| Exit-type verbs | `extras/zil_import/verbs/zil_sdk/movement.py` (walk dispatcher) |
| Stale-verb sweep | `moo/bootstrap/__init__.py` (`_remove_stale_repo_verbs`) |
| Mirror-state assertion | `extras/zil_import/scripts/zork1_smoke.py` (reset snippet) |
| Score variance | `extras/zil_import/scripts/zork1_smoke.py` (`_RESET_SNIPPET`) |
| Predicate sweep | `extras/zil_import/translator.py` (verb-name emission sites) |
