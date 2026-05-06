# Phase 3 backlog — ZIL importer refactor

Phase 1 (boat M-BEG fix without parser changes), Phase 2 (architecture
doc + leakage regression test), and several Phase 3 partials landed in
the 2026-05-03 session. This file tracks the remaining refactor items,
each independently shippable. Pair with `ARCHITECTURE.md` for the
architectural context and the hard rules.

## Status snapshot (2026-05-03)

**Done:**

- Phase 1 — boat M-BEG dispatch via System Object `do_command` verb
  (no parser/SDK changes). Smoke test reaches Phase E-4-d baseline.
- Phase 2 — `ARCHITECTURE.md` + 4 regression tests in
  `tests/test_no_zmachine_leakage.py`.
- Phase 3 partials:
  - **Item 6 partial** — pre-* verbs wired into syntax dispatch (no
    longer dead). `extras/zil_import/generator.py`.
  - **Item 5 partial** — runtime atom resolution via `lookup()` instead
    of `_.get_property()`. Atom-form aliases on every room/object;
    System Object property registry kept for bootstrap-time
    `--on $atom` shebang resolution only.
  - **Auto-import fix** — translator now scans param/aux default
    expressions for `lookup(`/`context.`/`random.`/`re.` patterns, not
    just body lines. Caught a latent missing-import bug in OTVAL-FROB.
  - Stale `confunc` docstring in `verbs/zil_sdk/queue_sdk.py` fixed.

**Verification:**

- `extras/zil_import/scripts/zork1_smoke.py` PASSes.
- `uv run pytest moo/ -n auto`: 2662 passed, 3 skipped.
- `uv run pytest extras/zil_import/tests/ moo/bootstrap/zork1/tests/ -n auto`:
  1435 passed.
- `git diff moo/core/parse.py` and `git diff moo/sdk/` both empty.

## Remaining items (pick one per session)

### Item 1 — Decompose god-verbs

**Highest structural win.** OBJECT-FUNCTION blocks like `$inflated_boat`
emit a single 30+-name god-verb whose body switches on `player_verb`
and `rarg`. Decomposing into per-verb files would:

- Drop `run_v_routine` fallthrough chains
- Drop the `rarg` lifecycle parameter
- Let DjangoMOO's parser do natural verb dispatch with `passthrough()`
  for substrate fallthrough
- Shrink `_global/object_handlers/` substantially

**Where to start:** `extras/zil_import/translator.py` `translate_routine`
and `translate_m_clause`. Add a third emission path that splits by
`player_verb` clauses. The IR (`ZilRoutine`) already has the routine
body; the translator's `_extract_m_clause` is a precedent for splitting.

**Risk:** medium-high. Many routines (50+ god-verbs to decompose). ZIL's
`player_verb in [...]` switches may have edge cases (cascading
clauses, shared aux state). Smoke test catches obvious breakage but
subtle routing issues could slip through. Recommend: decompose one
god-verb manually first to validate the pattern, then extend the
translator.

**Effort:** half-day to a day of focused work.

### Item 2 — Per-exit-type evaluation

ZIL has five exit types: UEXIT, NEXIT, FEXIT, CEXIT, DEXIT. They're
currently all stored as data on `$zork_exit` and traversed by
`_.zil_sdk.walk()`. Some map cleanly to verb-driven dispatch
(mirroring `default/verbs/exit/`); others may stay better as data.

**Sketch:**

- UEXIT (unconditional) → trivial: `$zork_exit.invoke(player)` calls
  `move()`.
- NEXIT (no-exit-message) → trivial: `$zork_exit.invoke(player)`
  prints the message and returns without moving.
- FEXIT (function exit) → keep data-driven; the function name is the
  important state.
- CEXIT (conditional on flag) → could go either way; gate inside
  `$zork_exit.move()` is fine.
- DEXIT (door exit gated by openbit) → keep data-driven; the door
  object is the important state.

**Where to start:** the `walk()` SDK helper in
`extras/zil_import/verbs/zil_sdk/movement.py`. Move UEXIT/NEXIT
traversal logic onto `$zork_exit` verbs (mirroring
`moo/bootstrap/default/verbs/exit/move.py`). Make `walk()` a thin
dispatcher that does `room.match_exit(dir).invoke(player)` for the
common case and falls back to data-driven traversal only for FEXIT/
CEXIT/DEXIT.

**Risk:** medium. Movement is core gameplay; subtle changes could
break navigation. Smoke test exercises movement extensively, so
regressions should surface quickly.

**Effort:** moderate.

### Item 3 — Clean up substrate v-routines on $zork_thing

Depends on item 2 partly (v_walk uses Z-machine exit-table opcodes
which item 2 replaces). Remaining cleanup:

- Drop the `v-` prefix on substrate verbs so the parser finds them by
  natural name (parser dispatch + `passthrough()` replace the
  `run_v_routine` indirection).
- Drop Z-machine primitives (`getpt`/`ptsize`/`UEXIT`/...) where the
  call sites are dead after item 2.

**Where to start:** translator emission of `v-X` shebangs in
`generator.py` and the substrate-verb files in
`moo/bootstrap/zork1/verbs/_global/substrate_verbs/`. After item 2,
many substrate v-routines will have no callers; can be deleted.

**Risk:** low-medium. Each substrate verb tested independently
already (translated-verb load tests).

**Effort:** moderate.

### Item 4 — zstate parser-state cleanup

`_global/parser/syntax_check.py`, `_global/parser/clause.py`,
`_global/helpers/parser.py`, `_global/helpers/many_check.py`, etc.
reimplement Z-machine parser internals that DjangoMOO doesn't need.

**Two options:**

- (a) Skip translation of these routines entirely. They're only
  reachable through ZIL parser entry points (MAIN-LOOP, PARSER) which
  DjangoMOO bypasses with its own parser.
- (b) Leave as dead code. They don't crash anything (zstate_get
  returns None for missing keys).

**Where to start:** decision is which routines are "parser-only" and
should be skipped. Curated list in `extras/zil_import/translator.py` or
`generator.py`. Skipping them removes ~50% of remaining primitive
leakage.

**Risk:** low (already dead code).

**Effort:** small (curate list + skip logic).

### Item 5 — Drop System Object atom registry entirely

The atom-form aliases now serve runtime lookup. The System Object
property registry is kept only for `--on $atom` shebang resolution at
verb-load time.

**Sketch:** modify `moo/bootstrap/__init__.py:220` so `--on $atom`
falls back to `lookup(atom)` if the System Object property isn't
present. Then drop the `_.set_property("atom", obj)` calls from
`generator.py` — every alias-resolvable atom is reachable.

**Risk:** medium. Bootstrap-loader change touches moo core (outside
the parse.py / sdk hard-rule scope but still core). Worth a design
conversation before doing it.

**Effort:** small.

### Item 6 — Pre-action verbs become subclass overrides (final form)

Item 6 partial wired pre-* into the syntax dispatch chain. The full
form: pre-checks move into the body of the relevant `take`/`drop`/
`put`/etc. verb on a Zork class, followed by `passthrough()` to the
substrate. Drops the separate `pre-` registration step entirely.

**Risk:** medium. Each pre-verb has a different relationship with its
v-routine; merging requires per-verb judgment.

**Effort:** moderate. Lower priority now that the wiring is correct.

### Item 7 — Drop getp/getpt/ptsize/exit-type tags

Strictly dependent on items 2 and 3 — these primitives only appear in
code that those items replace. Once items 2/3 land, run the leakage
test, find what's still using them, and clean up the leftovers.

**Effort:** small (cleanup pass).

## Boat-launch gaps still pending (2026-05-03 late)

After fixing M-BEG dispatch, direction-token compares, APPLY-of-action,
and player_verb-in-M-clauses (see "Translator wins" section below), the
smoke test extends to `launch` from inside the boat at Reservoir-South.
The dispatch chain reaches `goto(rm)` in `_global/helpers/goto.py` and
fails with "You can't go there without a vehicle." — the no-go-tell
fallback when the boat's `vtype` and the destination room's flags
don't line up. Three compounding gaps, in order:

### Gap A — Table extraction was dropping atom refs

**Fixed.** `extras/zil_import/converter.py:_extract_table_values` was
treating uppercase atoms as Z-machine internals and skipping them, so
RIVER-LAUNCH was emitted as `["PURE"]` instead of the 16-element
location-pair table. Now keeps atom refs (prefixed with `@`) and
prepends an explicit length for LTABLE. `_gen_tables` resolves the
`@`-prefixed atoms to runtime Object references via `_rooms` /
`_objects` dicts. Tables file moved from `015_` to `035_` so it loads
after rooms/objects exist. Stale `015_tables.py` is unlinked on regen.

### Gap B — COND in expression position emitted `cond(...)`

**Fixed.** Translator's `_translate_expr` had no COND branch; expression
COND fell through to default head-as-function-call and emitted an
undefined `cond(...)` call. Now translates to a chained ternary:
`(value1 if test1 else (value2 if test2 else value3))`. Caught when
`describe_room.py` started running at Reservoir-South after the
HERE→here() change shifted control flow into the cond branch.

### Gap C — `.var` flag-name deref emitted as string literal

**Fixed.** `<FSET? .RM .AV>` was emitting `flag(rm, ".av")` (string
literal) instead of `flag(rm, av)` (variable expression). Translator's
`_translate_flag_name` now detects `.X` where X is a routine
param/aux and emits the bare variable name.

### Gap D — VTYPE / NONLANDBIT not propagated

**Fixed (2026-05-03 even-later).** The boat's ZIL definition has `(VTYPE NONLANDBIT)` but the
converter doesn't extract VTYPE — `ZilObject` has no field for it.
Result: `getp(boat, "vtype")` returns None, `goto`'s vehicle-type
check fails, no-go-tell fires.

Fix sketch:

1. Add `vtype` field to `extras/zil_import/ir.py:ZilObject`
2. Extract `(VTYPE atom)` in `_extract_object`
3. Emit `obj.set_property("vtype", "NONLANDBIT")` in `_gen_objects`

But that's only half — also need:

1. `NONLANDBIT` (and friends like RWATERBIT, RAIRBIT) added to
   `ROOM_FLAG_PROPERTIES` so water rooms have the matching property
2. The `goto`-style `flag(rm, av)` calls then resolve correctly

There's also a runtime PUTP statement in the ZIL bootstrap routine
GO that does `<PUTP ,INFLATED-BOAT ,P?VTYPE ,NONLANDBIT>`. We're not
running that routine at bootstrap time, so even if the converter
emits the static VTYPE, any dynamic VTYPE updates need a different
mechanism.

### Gap E — `goto` helper multi-condition logic may need review

`_global/helpers/goto.py` checks several flag combinations (lb, av,
RLANDBIT, .av) before allowing the move. The current state of the
checks may need adjustment for our model — e.g. `flag(rm, "outdoor")`
behaves differently in DjangoMOO than ZIL's RLANDBIT semantics.
Trace through with a working VTYPE first and see what's left.

### Effort estimate

Gap D landed in ~30 minutes of self-paced work. Three other gaps
surfaced and got fixed alongside it (BTST primitive, M-FLASH/M-OBJDESC
apply mappings, empty-body M-clause emission overriding default
look). The whole launch sequence (Steps 2.4 SCEPTRE → BUOY → EMERALD
→ ATLANTIS) probably needs 1-2 more iterations of similar puzzle-
debug work; the buoy/emerald/atlantis legs will surface their own
translator gaps as the smoke test extends past "look at the lake".

## Boat-launch close (2026-05-03 even-later)

After Gap D landed three more gaps surfaced and got fixed:

- **BTST primitive translation.** `<BTST a b>` now translates to
  `((a or 0) & (b or 0)) != 0` (handles None values from
  unpopulated zstate keys). Companion BOR / BAND added too.
- **M-FLASH / M-OBJDESC mapping.** Translator's APPLY-of-action
  branch now handles all M-clause atoms. M-FLASH → ``flashfunc``
  and M-OBJDESC → ``descfunc`` map to verb names that have the
  has_verb guard, so the apply call becomes a safe no-op when the
  object has no flash/descfn handler. Previously these threw
  `NameError: apply` mid-describe-room.
- **Empty M-clause body skip.** When a ZIL routine's M-clause body
  is bare ``<>`` (RFALSE — "do nothing for this event, let default
  behavior continue"), the translator now emits no verb file at all.
  Previously it emitted a stub with the param/aux unpacking but
  empty body, which would WIN parser dispatch via last-match-wins
  and silently override the default substrate verb (e.g. boat's
  empty M-LOOK was blocking Reservoir.look from firing).

Smoke endpoint after these fixes:

```text
> launch
[empty — boat moves silently to Reservoir]
> look
Reservoir, in the magic boat
You are on the lake. Beaches can be seen north and south.
Upstream a small stream enters the lake through a narrow cleft
in the rocks. The dam can be seen downstream.
PASS
```

1429 zork1+importer tests pass after these fixes.

The next puzzle-debug iteration would extend the smoke test toward
drifting through the rivers, opening the buoy, and taking the emerald
— each step likely surfacing more translator gaps to fix.

## Boat-launch into river system (2026-05-03 still later)

Pivoted the smoke probe's launch point from Reservoir-South to Dam
Base so the launch sequence enters the river system proper
(RIVER-LAUNCH: `DAM-BASE → RIVER-1`).  Smoke now confirms:

- Navigation Living-Room → cellar → … → Dam-Room → down to Dam Base
- `board magic boat` works
- `go north` from inside the boat at Dam Base is blocked by
  preturnfunc with "Read the label..."
- `launch` moves player+boat to RIVER-1 silently
- `look` from RIVER-1 prints "You are on the Frigid River in the
  vicinity of the Dam. The river flows quietly here. There is a
  landing on the west shore."

### Gap F — Queue/clocker daemon-firing not implemented

**Fixed (2026-05-03 even-later-still).** The boat preturnfunc launch branch queues the i-river
daemon to drift the boat through RIVER-1 → RIVER-2 → … → RIVER-4
each turn.  In ZIL, `CLOCKER` runs after every command and ticks
all queued daemons; when their counters reach 1 it fires their
routines.

In our translation:

- `extras/zil_import/verbs/zil_sdk/queue_sdk.py` stores queue
  entries on `context.player` as `zstate_queue`, but nothing
  *processes* the queue.
- `clocker.py` was translated but uses undefined primitives
  (`rest`, `apply` for non-M-clause args) and reads C-TABLE / C-INTS
  / C-DEMONS — Z-machine internals we don't populate.
- `zstate_moves` (the turn counter) never increments because
  CLOCKER is what increments it.

**Fix sketch:**

1. Add a `tick` verb in `queue_sdk.py` that:
   - Increments `zstate_moves`
   - Iterates `zstate_queue`, decrements `fire_at_turn` for each entry
   - Fires routines whose counter has reached/passed 0 by invoking
     them on `$zork_thing`
2. Hook `tick` from a place that runs after every command.  Options:
   - Add a `turnfunc` verb on `$zork_thing` that calls
     `zil_sdk.tick()` then passes through to existing turnfuncs
   - Alternatively, make `system/do_command.py` call `tick()` at
     the end (post-dispatch from the do_command hook isn't quite
     "after dispatch" but close enough for daemons that don't care
     about command outcome)

**Effort:** medium.  Risk: low — daemons that aren't fired today
won't fire then either, so anything that breaks would have been
already broken.  Once Gap F lands, the smoke can extend with
several `wait` commands to drift the boat through the rivers.

**Implementation landed:**

- `extras/zil_import/verbs/zil_sdk/queue_sdk.py` gained a `tick`
  verb: increments `zstate_moves`, partitions queue into due/pending
  (saves pending so re-queuing daemons append to the new list), then
  fires due routines on `$zork_thing` with per-daemon try/except so
  a broken daemon doesn't crash the whole tick.
- `extras/zil_import/verbs/system/do_command.py` calls
  `_.zil_sdk.tick()` post-preturnfunc on every command.  Order
  caveat: tick fires *before* the dispatched verb runs (we can't
  hook post-dispatch without parse.py changes), so daemon side
  effects appear in output before the typed verb's output.  ZIL's
  CLOCKER runs post-dispatch; for the smoke test this ordering
  doesn't matter.
- `extras/zil_import/generator.py` now skips translating
  `CLOCKER` / `MAIN-LOOP` / `MAIN-LOOP-1` / `PARSER` (Z-machine
  internals that don't translate cleanly), and a static template at
  `extras/zil_import/verbs/_global/helpers/clocker.py` provides a
  CLOCKER replacement that calls `_.zil_sdk.tick()` and returns
  False — so V-WAIT's `while clocker:` loop runs the configured
  number of iterations.
- Smoke test reset clears `zstate_queue` and `zstate_moves` at run
  start so old broken daemons (i-forest-room, i-thief, …) don't
  carry over.

**Verified end-to-end:** smoke test now exercises the full launch
→ drift → death sequence:

```text
> launch                  (silent — boat moves to RIVER-1)
> look                    (Frigid River desc)
> wait
Time passes...
The flow of the river carries you downstream.
> wait
Time passes...
The flow of the river carries you downstream.
> wait                    (faster speeds at RIVER-3/4/5)
The flow of the river carries you downstream.
Time passes...
The flow of the river carries you downstream.
Unfortunately, the magic boat doesn't provide protection from
the rocks and boulders one meets at the bottom of waterfalls.
Including this one.
PASS
```

**Side effects of tick wiring:** the leakage `BASELINE` dropped
from 150 → 103 (Z-machine primitives removed because skipped
routines no longer emit code with P-LEXV / PRSA references).

### Other gaps observed

- The double "in the magic boat" in `look` output is a minor
  display issue — describe-room prints "Reservoir, in the magic
  boat" header AND Reservoir.look prints the desc.  Cosmetic.
- DAM-BASE has darkness in actual ZIL (no LIGHTBIT).  We bypass
  with `zstate_always_lit=True` in the smoke reset; future probes
  may need to handle real darkness via a lit lantern in inventory.

## Translator wins from boat-puzzle resumption (2026-05-03 evening)

When extending the smoke test for Step 2.4 (boat trip) three translator
gaps surfaced and got fixed:

1. **P? direction atoms.** ZIL stores direction codes in PRSO; in
   DjangoMOO the dobj is a string. Added `_DIRECTION_ATOMS` map in
   `translator.py` and an EQUAL?/IN? handler that detects `,PRSO` vs
   direction-atom comparisons and emits
   `context.parser.get_dobj_str() == "east"` etc.

2. **APPLY of action routine with an M-clause arg.** ZIL's
   `<APPLY <GETP obj ,P?ACTION> ,M-ENTER>` was emitting an undefined
   `apply()` call. Now translates to `obj.invoke_verb("enterfunc")`
   (with has_verb guard) when the M-clause arg matches a known verb
   in `_M_TO_VERB`. Other APPLY forms still fall through to bare
   `apply()` — these are dead code paths in the smoke test scope;
   will need a more general fix when another puzzle exercises them.

3. **player_verb in M-clauses.** `do_command` runs before
   `parser.verb` is resolved, so when it invokes `preturnfunc` the
   runtime-injected `player_verb` resolves to the invoked verb name
   ("preturnfunc") instead of the typed verb ("go"). Fix:
   - `system/do_command.py` now passes `parser.words[0]` as args[1]
     to preturnfunc invocations
   - Translator marks M-clause body translation with `_in_m_clause`
     flag and emits a `the_player_verb = args[1] if len(args) > 1
     else player_verb` binding at the top of M-clause bodies
   - PRSA references and `<VERB? …>` forms inside M-clauses use
     `the_player_verb` instead of `player_verb`

**Result:** boat dispatch verified end-to-end. Smoke test reaches
"Read the label for the boat's instructions." after `go north` from
inside the boat at Reservoir-South. 1435 zork1 tests + 54 importer
tests pass.

## Translator gap: P? direction atoms (discovered 2026-05-03)

When investigating Step 2.4 (boat trip), found a real translator gap that
surfaces specifically in the boat M-BEG handler. The boat preturnfunc
checks whether the player is trying to walk in a direction that should
be blocked:

```python
if context.parser.get_dobj() in (
    _.zil_sdk.zstate_get("P?LAND"),
    _.zil_sdk.zstate_get("P?EAST"),
    _.zil_sdk.zstate_get("P?WEST"),
):
    return False
```

**Problem:** `zstate_get("P?LAND")` returns `None` (zstate has no value
for that key — direction atoms are never seeded). And `get_dobj()`
returns an Object (or None), not a direction string. So the comparison
is always `Object in (None, None, None)` — always False, and the
"Read the label..." else branch always fires.

**ZIL context:** the original code does `<EQUAL? ,PRSO ,P?EAST>` where
PRSO holds a direction *token* (the ZIL parser stores direction codes
in PRSO when the player types "go east"). In DjangoMOO, "east" is the
dobj string, not an Object — `get_dobj_str() == "east"` would be the
right check.

**Fix sketch:**

1. Add a `_DIRECTION_ATOMS` map in `translator.py`: P?LAND→"land",
   P?NORTH→"north", P?EAST→"east", … translate these atoms to direction
   strings.
2. Detect the comparison context: when ZIL `<EQUAL?>` (or `<==?>`) has
   PRSO on one side and a direction atom on the other, emit
   `context.parser.get_dobj_str() == "direction"` instead of the
   Object-comparison form.
3. Same for the `<IN?>` form (Python `in` comparison).

**Why this matters now:** Step 2.4 of PHASE_E4E_PLAN.md (boat puzzle)
cannot be smoke-tested until this is fixed — the boat will misbehave on
every direction command. Other puzzles that do direction-conditional
logic likely have the same issue but are less visible.

**Where to look:** Compares involving PRSO are emitted by
`extras/zil_import/translator.py`'s `_translate_form` for COND/EQUAL?/
IN? patterns. The atom-translation site is the same `_translate_atom`
function that I modified in the lookup() migration.

**Effort:** moderate. Translator surgery with pattern detection. Once
fixed, regenerate and re-run the smoke test — expect to add Step 2.4
boat commands as the next extension.

## Hard rules to keep in mind

From `feedback_zil_translator_no_core_changes.md`:

1. **Never modify `moo/core/parse.py`** to support a translator gap.
2. **Never add a new function to `moo/sdk/`** to support a translator
   gap.
3. **Every translator change should shrink `extras/zil_import/verbs/zil_sdk/`
   and `moo/bootstrap/zork1/verbs/_global/substrate_*/`, not grow them.**
4. **No more god-verbs in new translator output.**

## Verification cadence

After each item:

```bash
uv run python -m extras.zil_import /Users/philchristensen/Workspace/zork1/zork1.zil
docker compose run --rm webapp manage.py moo_init --bootstrap zork1 --hostname zork1.local --sync
docker compose restart shell celery
uv run python -m extras.zil_import.scripts.zork1_smoke
uv run pytest extras/zil_import/tests/ moo/bootstrap/zork1/tests/ -n auto
```

The leakage test (`test_no_zmachine_leakage.py`) will fail when an
item shrinks the allowlist or the BASELINE count — update both as
ratchet evidence.
