# Phase 350 — From ~342/358 commands to 350/350 score

## Where we are (2026-05-06)

| Metric | Initial value | After Steps 4 + 5 | Target |
|---|---|---|---|
| Smoke commands passing | 342 / 358 | **358 / 358** ✅ | 358 / 358 |
| Smoke commands failing | 16 | **0** ✅ | 0 |
| Smoke score | 136 / 350 | **254 / 350** | 350 / 350 |
| Smoke rank | "Junior Adventurer" | **"Adventurer"** | "Master Adventurer" |
| Smoke total time | ~70s | 93s real (+30s `[no-suffix]` poll waits) | n/a |
| Slowest real-work command | n/a | < 0.4s ✅ | < 2s |
| `[no-suffix]` commands | n/a | `pray`, `light match`, `launch` (all 10s smoke poll, ~0.05s server) | n/a |

**The smoke now PASSES end-to-end.**  Steps 1, 3, 4, 5 from the original plan all landed.  The remaining gap to score 350 is no longer about smoke-test failures — it's about content (more treasures, room discovery bonuses, the endgame mini-game) which is largely out of scope per the "Out of scope" section below.

The smoke now runs the full 358-command journey end-to-end without crashing. The cascading "I don't know how to do that" / "There is no X here" failures that dominated earlier runs are gone — the do_command scenery resolver, open-container peek, and exit_move snake-case fixes opened the path. What remains is a mix of (a) translator bugs that produce *wrong* output for specific verbs, (b) game-state issues where the smoke trips over inventory weight, and (c) a structural translator gap on per-clause-split overlap.

## Why score is 0

The smoke score is 0 even though most commands succeed. Three causes, in priority order:

1. **No treasures reach the trophy case.** Many `take` commands fail with "Your load is too heavy" because the smoke's drop-cycle is brittle — when an earlier step fails (silently or otherwise), the player carries items they were supposed to drop, and the next pickup fails. Cascading state bug.
2. **Some treasures unreachable** — the boat doesn't drift to Sandy Beach (river daemon timing), so emerald / scarab / buoy / shovel are never picked up.
3. **Score-update hook may not be firing on trophy-case deposits.** Worth verifying directly — `score-obj` fires on first deposit, `tvalue` accumulates per item; if these aren't running, deposits register but score stays 0.

## The 16 failing commands, grouped by root cause

### A. Action-owner residual / per-clause overlap (1 failure)

- `open trap door` returns substrate "The trap door opens." instead of Zork-specific "rickety staircase…".

The trap-door's per-clause split (`open.py` for Living Room) and residual (`close.py` for Cellar branch) both register the verb name `open` on the trap door. Parser dispatch picks the lower-PK one (residual), which falls off in Living Room and passthrough()s to substrate v-open. **Documented as gap 10 in [.claude/skills/zil-import-training/references/open-gaps.md](../../.claude/skills/zil-import-training/references/open-gaps.md).**

### B. Translator bug: error message uses `desc` instead of name (1 failure)

- `tie rope to railing` returns `"You can't tie the A large coil of rope is lying in the corner. to that."`

The error template uses `rope.ldesc` ("A large coil of rope is lying in the corner") where it should use `rope.name` ("rope"). Look at the ZIL `D` print-spec — `<TELL "the " D ,PRSO ...>` should emit "the rope", not "the [ldesc]". Translator gap.

### C. Boat / river daemon timing (8 failures)

- `wait` ×2 — does not advance river daemon; boat doesn't drift.
- `look` ×2 — boat still at "vicinity of the Dam" instead of moving to RIVER-3 / RIVER-4.
- `go east` `'sandy'` — "White Cliffs prevent your landing" because boat is at wrong river segment.
- `disembark boat` — fatal because boat still in deep river.
- `take buoy/emerald/shovel/scarab` — never reach Sandy Beach.

The `i-river` daemon is queued but the smoke's `wait` commands aren't ticking it forward. Possible causes: (i) `do_command`'s `_.tick()` runs *before* `wait`'s body but the daemon may still need additional ticks; (ii) the i-river daemon isn't actually in the player avatar's zstate_queue after the boat is launched.

### D. Inventory weight (3 failures)

- `take coal`, `take diamond`, `take pot` — load too heavy.

These are downstream of the trophy-case drop-cycle being brittle. When the smoke walks past the trophy case carrying treasures, it should drop them; if any drop fails, weight accumulates.

### E. Misc (3 failures)

- `go north` `'mud pile'` — wrong room (Lake instead of post-dam location).
- `dig sand with shovel` — `I don't know how to do that.` — `dig` verb missing or shovel not in scope.
- `take scarab` — cascade from C.

## Roadmap to 350

The work splits into five steps. Each is independent and can be tackled in any order. Steps 1, 2, 4 raise the *command* pass count; step 3 unblocks the *score*. Step 5 is the structural cleanup the user requested (zil_sdk relocation).

### Step 1 — Combine per-clause + residual into single files

Touches `extras/zil_import/translator.py` + `generator.py`. When a routine has VERB? clauses *and* the residual nests VERB? checks for the same verb names, emit a single file per verb name with HERE-conditional branching. The residual no longer registers those verb names; per-clause splits aren't masked by the lower-PK residual.

Concrete plan:

1. In `_emit_routine`, after running `verb_clauses_for_split()` and before `translate()`, build a `verbs_in_residual` set from the residual body's nested `<VERB?>` checks.
2. For each verb in *both* `verb_clauses_for_split()` and `verbs_in_residual`, merge the residual's matching branch into the per-clause file (as an `elif` after the per-clause's HERE check).
3. Strip those verbs from the residual's shebang so it only registers the genuinely-leftover verb names.

Estimated impact: closes failure A. Same fix may help other action-owner objects with similar shapes (egg, mailbox, trap-door siblings).

### Step 2 — `D` print-spec uses `name`, not `ldesc`

Touches `extras/zil_import/translator.py`. ZIL's `<TELL ... D obj ...>` emits the object's short name with article. Currently we emit `obj.desc()` or similar that returns `ldesc`. Change to `obj.name` (or to a helper that picks the right field — `desc` for short name, `ldesc` for long description, `fdesc` for first-visit).

Verify against the canonical ZIL `D` semantics in `dungeon.zil` print-spec definitions.

Estimated impact: closes failure B and likely a handful of similar cosmetic mismatches not yet flagged by the smoke.

### Step 3 — Score-update hook: verify and unblock

Touches the smoke and possibly `verbs/zil_sdk/score.py`. Two parts:

1. Spot-test that `put bauble in case` / `put painting in case` actually credits score. If not, trace `score-update` / `score-obj` to find the gap. Likely candidate: the trophy-case `accept` verb invokes `score_update` but `score_update` reads from a state property that's never set.
2. Audit the smoke's drop-cycle. Each pre-deposit treasure pickup should be paired with a corresponding drop *before* the next heavy item. The current sequence likely has a missed-drop step that cascades into "load too heavy" failures D.

Estimated impact: closes failures D + lifts the score from 0 toward Junior Adventurer (≥30 points). The trophy-case drops are the gating step for ALL treasure score.

### Step 4 — River daemon ticking

Touches the smoke and `verbs/zil_sdk/queue_sdk.py`. The i-river daemon should fire on every tick once the boat is launched. Verify:

1. After `launch boat`, is `i-river` in the player avatar's `zstate_queue`?
2. Does `_.tick()` actually iterate the queue and decrement / fire entries?
3. Is the river-daemon body actually moving the boat, or short-circuiting on a state check?

If the queue mechanics work for shorter daemons (i-lantern dimming) but not i-river, the bug is daemon-specific. If no daemons are firing, the queue mechanic itself is broken.

Estimated impact: closes failures C (8 items) and downstream emerald / scarab / buoy / shovel.

### Step 5 — Relocate `zil_sdk/` into owner-based directories  ✅ done 2026-05-06

The `extras/zil_import/verbs/zil_sdk/` directory has been removed; each former SDK verb now lives under the directory matching its `--on` target (`verbs/system/`, `verbs/zork_root/`, `verbs/zork_actor/`, `verbs/zork_exit/`, `verbs/zork_thing/helpers/`).  Pure file relocation — no translator change needed because dispatch is keyed by the owner Object, not the file path.  Smoke pass count unchanged at 16/358 fail → confirmed structural-only.  Recorded in [.claude/skills/zil-import-training/references/completed-work.md](../../.claude/skills/zil-import-training/references/completed-work.md).

Original plan, kept for archaeology:

Touches `extras/zil_import/verbs/zil_sdk/*` (move) + `extras/zil_import/generator.py` (template-copy logic) + the leakage allowlist test. **End state: no `zil_sdk/` directory exists in the bootstrap output.** Each former zil_sdk verb lives under the directory matching its `--on` target.

Mapping (read from each file's shebang):

| File | `--on` | New location |
|---|---|---|
| `death.py` | `"System Object"` | `verbs/system/death.py` |
| `dispatch.py` | `"System Object"` | `verbs/system/dispatch.py` |
| `movement.py` | `"System Object"` | `verbs/system/movement.py` |
| `queue_sdk.py` | `"System Object"` | `verbs/system/queue.py` (rename: `_sdk` suffix becomes redundant) |
| `random_sdk.py` | `"System Object"` | `verbs/system/random.py` |
| `score.py` | `"System Object"` | `verbs/system/score.py` |
| `tables.py` | `"System Object"` | `verbs/system/tables.py` |
| `flags.py` | `"Zork Root"` | `verbs/zork_root/flags.py` (new dir) |
| `moveto.py` | `"Zork Root"` | `verbs/zork_root/moveto.py` |
| `output.py` | `"Zork Root"` | `verbs/zork_root/output.py` |
| `here.py` | `"Zork Actor"` | `verbs/zork_actor/here.py` |
| `state.py` | `"Zork Actor"` | `verbs/zork_actor/state.py` |
| `exit_move.py` | `"Zork Exit"` | `verbs/zork_exit/move.py` (new dir, rename to match owner-flat layout) |
| `is_held.py` | `$zork_thing` | `verbs/zork_thing/helpers/is_held.py` (already exists as topic dir) |

Implementation:

1. Move source files in `extras/zil_import/verbs/zil_sdk/*` to the corresponding new locations.
2. Update `extras/zil_import/generator.py`: the static-template copy step at `_TEMPLATE_VERBS_DIR.iterdir()` walks every subdir; relocate sources will land in the right place automatically as long as the directory tree mirrors the destination.
3. Translator emits calls like `_.zork_thing.is_held(...)` and `_.flag(...)` via attribute dispatch — those keep working because dispatch is on the *target object*, not the file path. **No translator change needed for the moves themselves.**
4. Update `extras/zil_import/tests/test_no_zmachine_leakage.py` `_KNOWN_PRIMITIVE_LEAKS` paths.
5. Delete `extras/zil_import/verbs/zil_sdk/` entirely (including `__init__.py`).
6. Regen + sync; verify `find moo/bootstrap/zork1/verbs/zil_sdk` returns nothing.
7. Run full smoke; expect identical pass count (this step is purely structural).

Estimated impact: zero functional change, but closes the long-standing "shrink zil_sdk over time" goal in [ARCHITECTURE.md](ARCHITECTURE.md) and removes the misleading "$zil_sdk is a real Object" mental model.

## Suggested order

1. **Step 5 first.** It's purely structural and reviewable in isolation — won't conflict with the other steps' substrate edits.
2. **Step 3 next.** Highest score impact for the least code change. If trophy-case deposits work today, the score gap is purely the drop-cycle audit in the smoke.
3. **Step 4.** River daemon. Once Step 3 lifts score above 0, this unlocks the second batch of treasures.
4. **Step 1.** The combined-clause refactor closes failure A and any latent siblings; non-trivial work but small blast radius.
5. **Step 2.** Cosmetic; do last.

## Verification

After each step, run:

```bash
uv run python -m extras.zil_import /Users/philchristensen/Workspace/zork1/zork1.zil --output moo/bootstrap/zork1
docker exec django-moo-shell-1 sh -c '/usr/app/bin/python /usr/app/src/manage.py moo_init --bootstrap zork1 --sync --hostname zork1.local'
uv run pytest extras/zil_import/tests/ -n auto
uv run python -m extras.zil_import.scripts.zork1_smoke 2>&1 | tee /tmp/smoke.out
grep -c "did not contain" /tmp/smoke.out
grep -E "rank of|Your score is" /tmp/smoke.out | tail -1
```

Track the pass count + score in [.claude/skills/zil-import-training/references/smoke-workflow.md](../../.claude/skills/zil-import-training/references/smoke-workflow.md) after each session.

The headline target is `Your score is 350` and rank `Master Adventurer`. Anything short of that means at least one treasure path is still incomplete.

## Out of scope for this phase

- Endgame post-win mini-game (different dispatch entirely).
- Translator-side decomposition of god-verbs into per-verb files (Phase 3 backlog item 1).
- Combat RNG reproducibility (lazy assertions cover thief/troll fights).
- Bauble path via thief AI (deferred indefinitely; smoke pre-sets `egg.open=True` as a shortcut).
