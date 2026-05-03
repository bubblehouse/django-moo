# Phase E-4-e — collect the remaining 16 Zork 1 treasures

## Context

The smoke test currently reaches **Phase E-4-d** (Amateur Adventurer rank, 4 treasures
deposited: painting + egg + torch + coffin) and ends with a clean PASS in ~55s.
The remaining work is to extend the test through the rest of Zork 1's treasures
until the score reaches 350 and the win banner fires.

This is one continuous extension — no architectural rewrites, just iteratively
adding command sequences and fixing whatever the translator/runtime gets wrong
along the way. Each puzzle is its own debug cycle: write the steps, run the
test, identify the failure, fix it (translator preferred), regenerate, sync,
re-run.

## What's left

16 treasures plus 3 nested bonuses, in roughly increasing difficulty:

| # | Treasure | Location | Puzzle | TVALUE |
|---|----------|----------|--------|--------|
| 1 | SCEPTRE | inside COFFIN | open coffin (already in inventory) | 6 |
| 2 | CANARY | inside EGG | open egg (already in inventory) | 4 |
| 3 | JADE | BAT-ROOM | carry GARLIC | 5 |
| 4 | DIAMOND | MACHINE-ROOM | put coal in machine, turn switch with screwdriver | 10 |
| 5 | SCARAB | SANDY-CAVE (INVISIBLE) | dig sand 3 times with shovel | 5 |
| 6 | TRIDENT | ATLANTIS-ROOM | navigate via small cave | 11 |
| 7 | CHALICE | TREASURE-ROOM | give water to cyclops, climb stairs | 5 |
| 8 | EMERALD | inside BUOY (in RIVER-4) | float boat downstream, open buoy | 10 |
| 9 | POT-OF-GOLD | END-OF-RAINBOW (INVISIBLE) | wave sceptre at rainbow | 10 |
| 10 | BRACELET | GAS-ROOM | navigate (no extinguished light source) | 5 |
| 11 | BAR | LOUD-ROOM | say echo to silence the room | 5 |
| 12 | BAG-OF-COINS | MAZE-5 | navigate the maze | 5 |
| 13 | TRUNK | RESERVOIR (INVISIBLE) | drain reservoir via dam controls | 5 |
| 14 | SKULL | LAND-OF-LIVING-DEAD | bell-book-candles ritual at LLD-ROOM | 10 |
| 15 | BAUBLE | (TBD — investigate) | TBD | 1 |
| 16 | (one to confirm) | | | |

Total of remaining TVALUE ≈ 100. Score also gains BASE-SCORE bonuses for
first-time treasure pickups (each treasure's VALUE) and first-time room
discovery (rooms with non-zero VALUE). Reaching 350 is the union of all of
these.

The thief (ROBBER) roams the dungeon and steals treasures — strategy is
"kill first, collect later." Killing the thief drops his bag with stolen
items. The thief carries the STILETTO; need a weapon (sword) to fight.

## Step 0 — `/grouped-commit` of current working dir

**First action**: stage and commit the in-progress Phase E-4-c/d changes so
this session has a clean tree before starting on E-4-e.

**Exclusion**: `moo/core/parse.py` must NOT be committed yet — the post-command
`endfunc` hook in that file is staged but pending review (the grouped-commit
skill needs to be told to leave it out of any group).

Everything else (importer changes, regenerated bootstrap, smoke test updates,
SSH disconnect logging fix) is committable.

## Step 1 — Sceptre + canary (zero-puzzle bonuses)

Easiest wins. Both are already in player inventory inside containers we
already collected.

```python
("open coffin", None),
("take sceptre", "Taken"),
("open egg", None),  # may need EGG-OBJECT permission check
("take canary", "Taken"),
```

EGG has TRYTAKEBIT and an EGG-OBJECT action; opening it without finesse
breaks it (BROKEN-EGG state). Verify the canonical `open egg` works without
breaking it. If it always breaks, deposit BROKEN-EGG + BROKEN-CANARY (still
score, lower TVALUE).

## Step 2 — Green-light puzzles (verbs known to translate)

Per the bootstrap-state audit, these puzzles have all the verbs and routines
in place. Add them in this order to the smoke test:

1. **Cyclops** (CHALICE): empty WATER from BOTTLE? Or just `give water to cyclops` if WATER object exists in scope. Then `up` to TREASURE-ROOM, `take chalice`.
2. **Machine room** (DIAMOND): walk to MACHINE-ROOM (path: cellar → south → east-of-chasm → east → gallery → north → studio → ... → coal mine area). Put coal in machine, turn switch with screwdriver, take diamond.
3. **Sandy cave** (SCARAB): get shovel, navigate to sandy cave, `dig sand with shovel` 3x, `take scarab`. **Stop at 3 — 4 digs collapse the cave (death).**
4. **Boat + Atlantis** (TRIDENT, EMERALD): inflate boat with pump at white cliffs, launch at reservoir-south, drift through river-1..4, open buoy in river-4, take emerald. Atlantis trident is reachable via small cave.
5. **Sceptre + Rainbow** (POT-OF-GOLD): take sceptre from coffin (Step 1), navigate to End of Rainbow (via Aragain Falls), `wave sceptre`, `take pot-of-gold`.
6. **Mirror** (transport, no treasure but used to reach gas room): rub mirror in mirror-room-1 to teleport between rooms.
7. **Bat room** (JADE): get GARLIC (kitchen, in lunch?), navigate to bat room, take jade.

Each puzzle, in order:

- Add commands to smoke test
- Run, observe failure, fix translator/runtime issue
- Repeat until that puzzle is clean

Expected fixes per puzzle: 0–2 small translator gaps each.

## Step 3 — Yellow-light puzzles (need translator review)

These were flagged by the bootstrap audit:

1. **Loud Room** (BAR): `say echo` requires SAY syntax with raw word token
   parsing. The current LOUD-ROOM-FCN reads tokens from P-LEXV directly,
   which the translator may have mishandled. Inspect `loud_room_fcn_*.py`,
   verify the `say echo` path. Likely fix: ensure SAY syntax handler passes
   the word through to the room's M-BEG/M-END.
2. **Dam controls** (TRUNK): `press button` and `turn bolt with wrench`.
   `push.py` syntax handler exists; verify `press` is a recognized synonym.
   The actual button objects (BLUE-BUTTON, RED-BUTTON, etc.) need their
   action handlers to fire on the right verb. Then `turn bolt with wrench`
   triggers BOLT-F to toggle gates → reservoir drains → TRUNK becomes
   visible after a turn delay.

## Step 4 — Red-light puzzles (missing infrastructure)

1. **Maze + bag of coins**: bootstrap audit found only `maze_5` directory;
   MAZE-1..MAZE-15 may not have generated room dirs. Investigate why.
   Likely cause: most maze rooms have no ACTION routine, so they get no
   `verbs/rooms/<slug>/` dir in the new layout — but the *room objects*
   should still exist in `020_rooms.py` and be navigable. If only the
   verb dirs are missing and the rooms themselves are present, navigation
   works fine. **Verify by inspecting 020_rooms.py for MAZE-1..15.**

2. **Land of the Dead ritual** (SKULL): V-RING substrate is a generic
   "Ding, dong" stub; the ritual logic in BELL-F + BLACK-BOOK + CANDLES-FCN
   relies on flags (XB, XC) that get set during `ring bell` / `light candles`
   / `read book` at LLD-ROOM. Trace through: bell becomes HOT-BELL after
   ring; XB-COUNTER starts; candles must be lit during the window; reading
   the book finishes the ritual and sets LLD-FLAG. Then walk through the
   gate to LAND-OF-LIVING-DEAD and take the skull.

   Path to LLD-ROOM: south temple → down → tiny cave (only if COFFIN-CURE
   is set, which means coffin is **not** in inventory at the time we
   descend). Means we need to deposit the coffin in the trophy case first,
   then come back without it.

3. **Bauble**: location TBD. Investigation needed — likely associated with
   the canary (the ZIL has CANARY → "songbird → bauble" gift on first wind).
   Worth checking before treating as a manual placement.

## Step 5 — Thief mitigation

The thief (ROBBER-FUNCTION) wanders the dungeon stealing treasures. Fight
him before he becomes a problem:

- The thief starts in TREASURE-ROOM (cyclops staircase destination).
- After the cyclops puzzle, kill him with the sword.
- His LARGE-BAG drops; collect any treasures he had.

Without this, treasures the test puts down (or that are in mid-pickup
rooms when the thief visits) get stolen and become inaccessible.

The smoke test should kill the thief immediately on entering Treasure
Room, not after the chalice. Sword + multiple `attack thief with sword`
turns until "thief is dead."

## Step 6 — Final deposit + win check

Once the test has visited every treasure source room, the player walks
back to Living Room with the cumulative inventory and deposits everything.
The trophy case `endfunc` recomputes the score on every put, so the final
check is straightforward:

```python
("score", "Master Adventurer"),  # rank at score=350
# or any close approximation if the actual sum lands at 348, 349, etc.
```

If 350 is reached, `*** You have won! ***` should fire from `score-upd`'s
post-condition (WON-FLAG check). The smoke test should also assert that
banner.

## Critical files to modify

- `extras/zil_import/scripts/zork1_smoke.py` — the test itself
- `extras/zil_import/scripts/zork1_smoke.py:_RESET_SNIPPET` — extend reset to include all treasures (currently only resets ones we use through E-4-d)
- `extras/zil_import/translator.py` — when a translator gap is found
- `extras/zil_import/generator.py` — same
- `moo/bootstrap/zork1/**` — regenerated bootstrap output (touched on every regen)

Do NOT touch `moo/core/parse.py` until the user gives the green light to
include the `endfunc` hook in a commit — it's currently uncommitted on
purpose.

## Verification

The smoke test is the single source of truth. Per puzzle:

```bash
# After translator/generator changes:
uv run python -m extras.zil_import /Users/philchristensen/Workspace/zork1/zork1.zil
docker-compose run --rm webapp manage.py moo_init --bootstrap zork1 --hostname zork1.local --sync
docker-compose restart shell celery
uv run python -m extras.zil_import.scripts.zork1_smoke
```

Expected: each new puzzle expands the PASSing prefix until the test ends
in `Master Adventurer` (score 350) and `*** You have won! ***`.

## Risk / time

Honest answer: open-ended. Each puzzle has a translator-bug rate that's
hard to predict. Best estimate based on the 4-treasure phases done so far:
~30–60 minutes per puzzle including investigation + translator fix +
regen + verification. 16 treasures × ~45 min = ~12 hours of focused work.

Speedups available:

- Multiple puzzles use the same V-routines (V-PUT, V-TAKE, V-OPEN) so a fix
  for one helps the rest.
- Once the M-END/endfunc dispatch is reliable, scoring "just works" for
  every deposit.

## Out of scope

- Save/restore commands (different dispatch entirely)
- Endgame post-win mini-game
- Combat RNG reproducibility — accept that thief/troll fights may need
  multiple `attack` rounds, asserted lazily
