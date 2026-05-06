# Phase E-4-e — collect the remaining Zork 1 treasures

## Status (2026-05-05, updated mid-session)

The smoke test reaches **score 96 / 350**, runs in ~70s, ends with a
clean PASS.  17 of 19 treasure entries deposited; bar parked at Atlantis
during the trident swap is recoverable but currently skipped, and the
bauble requires the thief to open the egg cleanly.

| # | Treasure | TVALUE | Status |
|---|----------|--------|--------|
| 1 | painting | 4 | ✅ deposited |
| 2 | broken_egg + broken_canary | 2 + 1 | ✅ deposited |
| 3 | torch (ivory) | 6 | ✅ deposited |
| 4 | coffin | 15 | ✅ deposited |
| 5 | sceptre | 6 | ✅ deposited |
| 6 | chalice | 5 | ✅ deposited |
| 7 | jade figurine | 5 | ✅ deposited |
| 8 | sapphire bracelet | 5 | ✅ deposited |
| 9 | platinum bar | 5 | ⚠️ parked at Atlantis (trident detour swap) |
| 10 | diamond | 10 | ✅ deposited |
| 11 | pot of gold | 10 | ✅ deposited (sceptre at End of Rainbow) |
| 12 | emerald | 10 | ✅ deposited (open buoy at SANDY-BEACH) |
| 13 | scarab | 5 | ✅ deposited (dig sand 3× — stop at 3) |
| 14 | bag of coins | 5 | ✅ deposited (Troll Room → MAZE-1 → 2 → 3 → up to 5) |
| 15 | trunk of jewels | 5 | ✅ deposited (yellow button → wrench → bolt → wait → drained reservoir) |
| 16 | trident | 11 | ✅ deposited (Mirror Room 1 → Small Cave → DOWN → Atlantis; bar swap) |
| 17 | skull | 10 | ✅ deposited (bell-book-candles ritual at Entrance to Hades) |

**Remaining (target +6 score points):**

| # | Treasure | Location | Puzzle | TVALUE |
|---|----------|----------|--------|--------|
| 18 | bauble | forest after winding canary | requires thief to open egg cleanly | 1 |
| -- | bar recovery | parked at Atlantis | second mirror swap to re-reach MR1 | 5 |

### Trident — solved via bar swap

Mirror Room 1 → east → Small Cave → DOWN → Atlantis Room.  Drop the
platinum bar (size 20) at Atlantis to free weight, take the trident
(size 20) in its place — net inventory delta zero, mining run unaffected.
Return path is asymmetric: Atlantis → up returns to Small Cave (LDESC
"tiny cave..."), then west → Twisting Passage → north → Mirror Room 1
→ north → Cold Passage.

### Skull — solved via 4-step ritual

Path: Living Room → trap door → Cellar → Troll Room → ... → Round Room
→ (matchbook detour: NS → Deep Canyon → Dam Lobby) → Engravings → Dome
→ Torch Room → North Temple (take bell) → South Temple (take book +
candles, then DOWN — works because COFFIN-CURE is set after coffin
deposit) → Tiny Cave → DOWN → Entrance to Hades.

Ritual at Entrance to Hades (LLD-ROOM):

1. `ring bell` — sets XB, swaps bell → hot-bell, queues I-XB
2. `light match` — sets FLAMEBIT + ONBIT on match (MATCH-FUNCTION)
3. `light candles` — auto-uses lit match, sets candles ONBIT
4. `read book` — LLD-ROOM M-BEG sees XB + candles ONBIT and sets XC;
   the read then triggers BLACK-BOOK and sets LLD-FLAG = T

Then `go in` → Land of the Living Dead → `take skull` → return via
Tiny Cave → north (Mirror Room 2) → Narrow Passage → Round Room → ...
→ Cellar → up → Living Room → put skull in case.

### Bauble — blocked on thief AI

The bauble drops when the player winds an *unbroken* canary in a forest
room (CANARY-OBJECT in actions.zil).  Every player-side path to open the
jewel-encrusted egg breaks it (BAD-EGG; both broken_egg and
broken_canary are then in play instead of the unbroken originals).  The
thief is the only NPC that can open the egg cleanly (sets EGG-SOLVE=T,
FSET ,EGG ,OPENBIT in the loot-distribution path), and the thief AI's
movement / pickpocket cycle is too random to drive from a smoke script.
Defer until the thief is exercised in a separate test.

### Trident — multiple blockers (deferred)

Two compounding issues:

1. **Weight.** The trident's `size=20` doesn't fit in the mining-path
   inventory (after picking jade/bracelet/diamond/coal alongside
   pre-mining items, total reaches 103 > LOAD-MAX 100). Tried
   dropping garlic, sword, axe, rope at first Bat Room visit — still
   too heavy because bar (size 20) and torch (size 20) are
   immovable along the lit-mining path.
2. **Mirror state.** Tried doing the Atlantis detour AFTER the
   pot-of-gold + trunk deposits, when inventory is light. But the
   first `rub mirror` during mining (Mirror Room 2 → Mirror Room 1)
   moved the mirror object itself to Mirror Room 1. A second visit
   to Mirror Room 2 then finds no mirror to rub. To take the
   trident, the player has to reach Mirror Room 1 directly — through
   Cold Passage (south from Cold Passage) or Twisting Passage (north).
   Cold Passage path requires a Mine Entrance detour.

Options to resolve:

1. **Take trident *before* mining** (at the existing rub-mirror step
   right before the mining pass). Then drop something heavy from
   inventory before continuing. Constraint: bar (size 20, picked at
   Loud Room) is the heaviest thing the smoke carries through gas
   room. Dropping bar at Bat Room and re-acquiring on the return
   pass might work.
2. **Reach Mirror Room 1 via Cold Passage** in the post-pot-of-gold
   detour: Cellar → ... → Mine Entrance → south (Slide) → east
   (Cold Passage) → south (Mirror Room 1) → east (Small Cave) →
   south (Atlantis) → return.

Option 2 is the cleaner detour but adds ~10 commands. Implement next
session.

### Generator multi-action fix (this session)

The translator's BUTTON-F routine is shared by 4 button objects
(yellow, brown, red, blue). The generator emits one verb file per
action_owner, but `_routine_to_filename(name)` returned the same
`button_f.py` for every owner — so the file got overwritten 3 times
and only the last shebang's `--on $blue_button` survived.

Fix at [generator.py:884-922](generator.py): prefix the extra-owner
verb file with `<owner_atom>__` so each owner gets its own file
(`yellow_button__button_f.py`, `red_button__button_f.py`, etc.).
Without this, `press yellow button` falls through to the substrate
v_press ("Pushing the X isn't notably helpful").

## What landed this session

**Translator/generator improvements** (now committed-equivalent — clean
regen produces only 13 file deltas, all legitimate):

1. **`<RFALSE>` in player-verb dispatch** ([translator.py:744-758](translator.py)) —
   inside an ACTION routine handling player verbs (e.g. TREASURE-INSIDE on
   the buoy), `<RFALSE>` now emits `return _.zil_sdk.run_v_routine(player_verb)`
   so the substrate `v-open` runs and sets `open=True`. Previously bare
   `return False` skipped the substrate entirely. Gated on `not _in_m_clause`
   so M-END/M-BEG turnfunc handlers keep their original `return False`
   semantics.
2. **`<APPLY .AV ,M-LOOK>` recursion guard** ([translator.py:1052-1075](translator.py)) —
   the emitted `has_verb("look")` check now uses `recurse=False`, so vehicles
   without their own M-LOOK clause don't dispatch to the inherited V-LOOK
   substrate. Without this, `look` while in the boat infinitely recursed
   describe-room until Python's stack limit hit.
3. **Substrate include via manifest** — discovery: a naive
   `python -m extras.zil_import dungeon.zil actions.zil` skips the
   ZIL substrate library and produces 430+ stale-file changes. Correct
   invocation is `python -m extras.zil_import zork1.zil` (the manifest),
   which `_expand_manifest` follows into `../zork-substrate/`. Output:
   439 routines (was 190), 140 objects (was 122), 132 syntax commands
   (was 0). **The 430-file regen panic was input misconfiguration, not
   accumulated drift.**

**Parser improvement** ([parse.py:524-552](../../moo/core/parse.py)):

+ `get_pronoun_object` now matches the caller's location by name or
  alias as a final fallback. Lets `disembark boat`, `look at boat`,
  `disembark raft` work when the player is inside the named object.
  In-scope objects always win because this is a `find_object` fallback.

**Smoke harness cleanup** ([scripts/zork1_smoke.py](scripts/zork1_smoke.py)):

+ Replaced the `@@disembark` out-of-band hack with the real game command
  `disembark boat`. Removed the `_disembark_player`, `_DISEMBARK_SNIPPET`,
  `_shell_exec` helpers and the `@@`-handling branch from the command loop.
+ Pot-of-gold detour added: Living Room → Kitchen → Behind House →
  Clearing → Canyon View → Cliff Middle → Canyon Bottom → End of Rainbow,
  `wave sceptre`, `take pot`, return path uses `southwest` (not `south`)
  and `northwest` from Canyon View (its `west` exit goes into the forest).
+ Boat-drift timing tuned: `wait, wait, look, go-east` is the exact tick
  budget to land at SANDY-BEACH (R3 → drift → R4 → walk east → SANDY-BEACH).

## Active workarounds (in-game)

+ **Boat-drift timing fragility** — the river-daemon tick budget is
  non-obvious; the smoke encodes it as a hard-coded sequence. Adding any
  command between `wait #2` and `go east` drifts the boat to RIVER-5,
  landing at SHORE instead. Could be replaced with a polling helper that
  detects "boat is at RIVER-4" and only then issues `go east`, but YAGNI.
+ **Score drift between runs** — sometimes the same smoke gives 164,
  sometimes 69. Suspected cause: trophy-case contents persist across
  smoke runs and `score-obj` (one-shot first-pickup bonus) doesn't fire
  for items already in inventory or already in the case. Fix: extend the
  reset snippet to move trophy-case contents back to their original
  rooms before each run. Not blocking but should be fixed before adding
  more puzzles.

## Remaining treasures — strategy

### 14. Trident (Atlantis)

Atlantis-Room is reached from RIVER-2 via south exit (swim) or via the
small cave system. The boat punctures on the trident on pickup (sharp
object), so trident must be taken *after* exiting the boat. Likely
path: drift R1→R2, get out at RIVER-2 (swim south? or land?), navigate
to Atlantis, take trident.

Verify the swim mechanic — V-DISEMBARK at RIVER-2 likely refuses
("getting out here would be fatal" — RIVER-2 isn't outdoor). May need
to climb out via RIVER-2's south exit which leads to Atlantis-Room
directly.

Score: +11 TVALUE + ~5 first-pickup bonus + room discovery.

### 15. Bag of coins (Maze)

The maze (MAZE-1..MAZE-15) has only `verbs/rooms/maze_5/` generated —
other maze rooms have no ACTION routine and so produce no verb dir.
Rooms themselves exist in `020_rooms.py` and exits in `040_exits.py`,
so navigation works fine.

Map-from-source the canonical solution sequence and hard-code it in the
smoke. Bag of coins is at MAZE-5 along with skeleton + skeleton key.

Score: +5 TVALUE + room bonuses.

### 16. Trunk of jewels (Reservoir drain)

Dam controls puzzle:

+ MAINTENANCE-ROOM is reached (already in smoke for screwdriver pickup).
+ `turn bolt with wrench` → BOLT-F toggles dam gates.
+ Reservoir drains (BUBBL daemon? confirm).
+ Walk through drained reservoir → take trunk (invisible while flooded).

Confirm gate→drain mechanism translates correctly. Screwdriver is
already in inventory.

Score: +5 TVALUE.

### 17. Skull (Land of the Living Dead ritual)

The hardest. Bell-book-candles sequence:

+ Path: South Temple → down → Tiny Cave (only when COFFIN-CURE set —
  coffin is **not** in inventory, ✓ already deposited).
+ At LLD-ROOM: `ring bell` (BELL-F sets HOT-BELL, queues XB-COUNTER),
  `light candles` (during window), `read book` (BLACK-BOOK sets
  LLD-FLAG).
+ Walk through gate → LAND-OF-LIVING-DEAD → take skull.

V-RING substrate is a generic "Ding, dong" stub. Real ritual logic is in
BELL-F + BLACK-BOOK + CANDLES-FCN. Verify each fires.

Score: +10 TVALUE.

### 18. Bauble

Location TBD. ZIL has CANARY → "songbird → bauble" gift on first wind.
Likely tied to winding the canary at a specific room (probably forest
or clearing — songbird only sings outdoors). Investigate.

Score: +1 TVALUE.

## Verification

```bash
# After translator/generator/bootstrap changes:
uv run python -m extras.zil_import /Users/philchristensen/Workspace/zork1/zork1.zil
docker compose run --rm webapp manage.py moo_init \
  --bootstrap zork1 --hostname zork1.local --sync
docker compose restart shell celery
uv run python -m extras.zil_import.scripts.zork1_smoke
```

Each new puzzle expands the PASSing prefix until the test reaches
`Master Adventurer` (350) and `*** You have won! ***`.

## Out of scope

+ Save/restore commands (different dispatch entirely).
+ Endgame post-win mini-game.
+ Combat RNG reproducibility — accept that thief/troll fights may need
  multiple `attack` rounds, asserted lazily.
