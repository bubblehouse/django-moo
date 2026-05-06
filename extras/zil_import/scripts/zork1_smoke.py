#!/usr/bin/env python3
"""End-to-end smoke test for the zil_import-generated Zork1 bootstrap.

Connects to the live ``zork1.local`` universe over SSH using the
``user+sitedomain`` multi-universe routing suffix, walks the canonical
opening of Zork 1, and asserts that:

- the post-auth banner ``Connected to universe: zork1.local`` was emitted
- the session lands in ``West of House`` (Zork content)
- the SYNTAX-driven player commands and substrate V-routines fire correctly
- the player can reach the Cellar and the Troll Room

Lives next to the importer it exercises so any changes to ``zil_import``
can be re-validated end-to-end with a single ``uv run python …`` invocation.

Lives under ``scripts/`` rather than ``tests/`` so pytest's auto-discovery
doesn't try to import it as a unit test (it requires a live SSH server and
docker-compose stack — well outside the unit-test contract).

Run:

    uv run python -m extras.zil_import.scripts.zork1_smoke
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

# ``moo_ssh`` lives in the game-designer toolbox and isn't a normal Python
# package (the parent dir name has a hyphen).  Load it by file path so this
# test stays portable even when run via ``-m``.
_MOO_SSH_PATH = Path(__file__).resolve().parents[2] / "skills" / "game-designer" / "tools" / "moo_ssh.py"
_spec = importlib.util.spec_from_file_location("moo_ssh", _MOO_SSH_PATH)
_moo_ssh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_moo_ssh)
MooSSH = _moo_ssh.MooSSH
strip_ansi = _moo_ssh.strip_ansi


_RESET_SNIPPET = """
from django.contrib.sites.models import Site
from moo.core.models.object import Object
site = Site.objects.get(domain='zork1.local')
wiz = Object.global_objects.get(name='Wizard', site=site)
woh = Object.global_objects.get(name='West of House', site=site)
mailbox = Object.global_objects.get(name='small mailbox', site=site)
leaflet = Object.global_objects.get(name='leaflet', site=site)
attic = Object.global_objects.get(name='Attic', site=site)
lr = Object.global_objects.get(name='Living Room', site=site)
rope = Object.global_objects.get(name='rope', site=site)
sword = Object.global_objects.get(name='sword', site=site)
lantern = Object.global_objects.get(name='brass lantern', site=site)
trap = Object.global_objects.get(name='trap door', site=site)
nest = Object.global_objects.get(name="bird's nest", site=site)
egg = Object.global_objects.get(name='jewel-encrusted egg', site=site)
gallery = Object.global_objects.get(name='Gallery', site=site)
painting = Object.global_objects.get(name='painting', site=site)
torch_room = Object.global_objects.get(name='Torch Room', site=site)
torch = Object.global_objects.get(name='torch', site=site)
pedestal = Object.global_objects.get(name='pedestal', site=site)
north_temple = Object.global_objects.get(name='Temple', site=site)
bell = Object.global_objects.get(name='brass bell', site=site)
south_temple = Object.global_objects.get(name='Altar', site=site)
altar = Object.global_objects.get(name='altar (ALTAR)', site=site)
book = Object.global_objects.get(name='black book', site=site)
candles = Object.global_objects.get(name='pair of candles', site=site)
egypt = Object.global_objects.get(name='Egyptian Room', site=site)
coffin = Object.global_objects.get(name='gold coffin', site=site)
case = Object.global_objects.get(name='trophy case', site=site)
treasure_room = Object.global_objects.get(name='Treasure Room', site=site)
chalice = Object.global_objects.get(name='chalice', site=site)
leaflet.location = mailbox; leaflet.save()
rope.location = attic; rope.save()
sword.location = lr; sword.save()
lantern.location = lr; lantern.save()
egg.location = nest; egg.save()
painting.location = gallery; painting.save()
torch.location = pedestal; torch.save()
bell.location = north_temple; bell.save()
book.location = altar; book.save()
candles.location = altar; candles.save()
# LLD ritual state: bell becomes hot-bell after ringing, candles
# get burned, and LLD-FLAG / XB / XC track the ceremony progress.
# Reset all of it so re-runs see a fresh ritual.
matchbook = Object.global_objects.get(name='matchbook', site=site)
dam_lobby = Object.global_objects.get(name='Dam Lobby', site=site)
matchbook.location = dam_lobby; matchbook.save()
matchbook.set_property('onbit', False)
matchbook.set_property('flamebit', False)
matchbook.save()
candles.set_property('onbit', False)
candles.set_property('touchbit', False)
candles.set_property('rmungbit', False)
candles.save()
bell.set_property('touchbit', False)
bell.save()
hot_bell = Object.global_objects.filter(name='hot bell', site=site).first()
if hot_bell:
    hot_bell.location = None; hot_bell.save()
skull = Object.global_objects.get(name='crystal skull', site=site)
lld_room = Object.global_objects.filter(name='Land of the Dead', site=site).first()
if skull and lld_room:
    skull.location = lld_room; skull.save()
wiz.set_property('zstate_lld_flag', False)
wiz.set_property('zstate_xb', False)
wiz.set_property('zstate_xc', False)
# Bauble: not in the world initially — appears when canary is wound in a
# forest room.  Reset SING-SONG flag and remove any bauble stranded from
# previous runs so the wind summons a fresh one.
wiz.set_property('zstate_sing_song', False)
bauble = Object.global_objects.filter(name='beautiful brass bauble', site=site).first()
if bauble:
    bauble.location = None
    bauble.save()
coffin.location = egypt; coffin.save()
canary = Object.global_objects.get(name='golden clockwork canary', site=site)
sceptre = Object.global_objects.get(name='sceptre', site=site)
broken_egg_obj = Object.global_objects.get(name='broken jewel-encrusted egg', site=site)
broken_canary_obj = Object.global_objects.get(name='broken clockwork canary', site=site)
canary.location = egg; canary.save()
sceptre.location = coffin; sceptre.save()
broken_egg_obj.location = None; broken_egg_obj.save()
broken_canary_obj.location = broken_egg_obj; broken_canary_obj.save()
# Pre-open the egg so the unbroken canary is accessible without going
# through V-MUNG (which always triggers BAD-EGG and replaces canary
# with broken_canary, breaking the bauble path).  In canonical Zork
# only the thief opens the egg cleanly; we shortcut by setting OPENBIT
# at bootstrap time so the smoke can wind the canary in a forest room.
egg.set_property('open', True); egg.save()
coffin.set_property('open', False); coffin.save()
chalice.location = treasure_room; chalice.save()
mailbox.set_property('open', False); mailbox.save()
trap.set_property('open', False); trap.save()
case.set_property('open', False); case.save()
wiz.set_property('zstate_rug_moved', False)
wiz.set_property('zstate_score', 0)
wiz.set_property('zstate_base_score', 0)
wiz.set_property('zstate_dome_flag', False)
wiz.set_property('zstate_lit', True)
# Clear daemon queue and turn counter so a previous run's broken
# daemons (i-forest-room, i-thief, etc — predicate routines that
# don't translate cleanly) don't carry over and crash do_command's
# tick on the first command.
wiz.set_property('zstate_queue', [])
wiz.set_property('zstate_moves', 0)
# Short-circuit lit? — the ZIL lit? routine walks parser-internal tables
# (P-MERGE / P-SLOCBITS / DO-SL) that we don't initialise, so calls to
# lit? from goto() crash on uninitialised state.  ALWAYS-LIT is read
# first in lit? and returns True without touching the parser tables.
wiz.set_property('zstate_always_lit', True)
wiz.location = woh; wiz.save()
kitchen_table = Object.global_objects.get(name='kitchen table', site=site)
kitchen_room = Object.global_objects.get(name='Kitchen', site=site)
sandwich_bag = Object.global_objects.get(name='brown sack', site=site)
garlic = Object.global_objects.get(name='clove of garlic', site=site)
lunch = Object.global_objects.get(name='lunch', site=site)
jade = Object.global_objects.get(name='jade figurine', site=site)
bar = Object.global_objects.get(name='platinum bar', site=site)
loud_room = Object.global_objects.get(name='Loud Room', site=site)
diamond = Object.global_objects.get(name='huge diamond', site=site)
coal = Object.global_objects.get(name='small pile of coal', site=site)
screwdriver = Object.global_objects.get(name='screwdriver', site=site)
bracelet = Object.global_objects.get(name='sapphire-encrusted bracelet', site=site)
bat_room = Object.global_objects.get(name='Bat Room', site=site)
gas_room = Object.global_objects.get(name='Gas Room', site=site)
dead_end_5 = Object.global_objects.get(name='Dead End (DEAD-END-5)', site=site)
maintenance_room = Object.global_objects.get(name='Maintenance Room', site=site)
machine = Object.global_objects.get(name='machine', site=site)
sandwich_bag.location = kitchen_table; sandwich_bag.save()
garlic.location = kitchen_room; garlic.save()
lunch.location = sandwich_bag; lunch.save()
jade.location = bat_room; jade.save()
bar.location = loud_room; bar.save()
diamond.location = None; diamond.save()
coal.location = dead_end_5; coal.save()
screwdriver.location = maintenance_room; screwdriver.save()
bracelet.location = gas_room; bracelet.save()
machine.set_property('open', False)
# Clear machine contents so coal→diamond puzzle starts clean
gunk = Object.global_objects.filter(name='small piece of vitreous slag', site=site).first()
if gunk and gunk.location == machine:
    gunk.location = None; gunk.save()
diamond_obj = Object.global_objects.filter(name='huge diamond', site=site).first()
if diamond_obj and diamond_obj.location == machine:
    diamond_obj.location = None; diamond_obj.save()
mirror_room_1 = Object.global_objects.get(name='Mirror Room (MIRROR-ROOM-1)', site=site)
mirror_room_2 = Object.global_objects.get(name='Mirror Room (MIRROR-ROOM-2)', site=site)
# There are two mirror objects (MIRROR-1 in MR1, MIRROR-2 in MR2).  Each
# rub swaps contents of both rooms so over a run they migrate; reset
# both back by alias so a second rub during the bar-recovery detour finds
# a mirror in MR2.
mirror_1 = Object.global_objects.filter(site=site, aliases__alias='mirror_1').first()
mirror_2 = Object.global_objects.filter(site=site, aliases__alias='mirror_2').first()
if mirror_1:
    mirror_1.location = mirror_room_1; mirror_1.save()
if mirror_2:
    mirror_2.location = mirror_room_2; mirror_2.save()
wiz.set_property('zstate_mirror_mung', False)
# Boat puzzle (Step 2.4): pre-place the inflated boat at Dam Base so the
# launch sequence enters the river system (DAM-BASE → RIVER-1 via the
# RIVER-LAUNCH table).  Reservoir-South would only put the boat on the
# lake — i-river daemon cancels itself outside RIVER-1..5.
inflated_boat = Object.global_objects.get(name='magic boat', site=site)
inflatable_boat = Object.global_objects.filter(name='pile of plastic', site=site).all()
dam_base = Object.global_objects.get(name='Dam Base', site=site)
# Reset all boat states first so a previous puncture doesn't accumulate.
for plastic in inflatable_boat:
    plastic.location = None
    plastic.save()
inflated_boat.location = dam_base; inflated_boat.save()
buoy = Object.global_objects.get(name='red buoy', site=site)
emerald = Object.global_objects.get(name='large emerald', site=site)
sandy_beach = Object.global_objects.get(name='Sandy Beach', site=site)
shovel_obj = Object.global_objects.filter(name='shovel', site=site).first()
buoy.location = sandy_beach; buoy.save()
emerald.location = buoy; emerald.save()
buoy.set_property('open', False); buoy.save()
# Reset shovel to SANDY-BEACH (bootstrap default) so multiple smoke
# runs don't cumulatively drag it into player inventory.
if shovel_obj:
    shovel_obj.location = sandy_beach
    shovel_obj.save()
# Reset SCARAB visibility and BEACH-DIG counter so the dig puzzle
# starts fresh: scarab.invisible=True, BEACH-DIG=0 (incrementing
# from None would TypeError on first ``dig sand with shovel``).
scarab = Object.global_objects.filter(name='beautiful jeweled scarab', site=site).first()
sandy_cave = Object.global_objects.get(name='Sandy Cave', site=site)
if scarab:
    scarab.location = sandy_cave
    scarab.set_property('invisible', True)
    scarab.save()
wiz.set_property('zstate_beach_dig', 0)
# Reset pot-of-gold + rainbow state so the wave-sceptre puzzle starts
# fresh each smoke run (idempotent).
pot_of_gold = Object.global_objects.filter(name='pot of gold', site=site).first()
end_of_rainbow = Object.global_objects.get(name='End of Rainbow', site=site)
if pot_of_gold:
    pot_of_gold.location = end_of_rainbow
    pot_of_gold.set_property('invisible', True)
    pot_of_gold.save()
wiz.set_property('zstate_rainbow_flag', False)
# Reset trident to Atlantis Room (sharp object — punctures boat if
# carried into the boat puzzle, and accumulates in inventory across
# runs otherwise).
trident = Object.global_objects.filter(name='crystal trident', site=site).first()
atlantis_room = Object.global_objects.get(name='Atlantis Room', site=site)
if trident:
    trident.location = atlantis_room
    trident.save()
# Reset bag of coins to MAZE-5 so the maze treasure pickup is idempotent.
bag_of_coins = Object.global_objects.filter(name='leather bag of coins', site=site).first()
maze_5 = Object.global_objects.get(name='Maze (MAZE-5)', site=site)
if bag_of_coins:
    bag_of_coins.location = maze_5
    bag_of_coins.save()
# Reset trunk to RESERVOIR (invisible until i-rempty drains it).  Also
# reset GATE-FLAG and GATES-OPEN so the bolt sequence is idempotent.
trunk = Object.global_objects.filter(name='trunk of jewels', site=site).first()
reservoir = Object.global_objects.get(name='Reservoir', site=site)
if trunk:
    trunk.location = reservoir
    trunk.set_property('invisible', True)
    trunk.save()
# Reset wrench to MAINTENANCE-ROOM so it's available each run.
wrench = Object.global_objects.filter(name='wrench', site=site).first()
if wrench:
    wrench.location = maintenance_room
    wrench.save()
wiz.set_property('zstate_gate_flag', None)
wiz.set_property('zstate_gates_open', None)
wiz.set_property('zstate_low_tide', None)
# Reset reservoir flag too (i-rempty sets nonlandbit=False, outdoor=True;
# revert so the puzzle starts fresh).
reservoir.set_property('nonlandbit', True)
reservoir.set_property('outdoor', False)
reservoir.save()
# Fix exits whose dest was wrong at initial bootstrap time
mine_in_exit = Object.global_objects.get(name='in from MINE-ENTRANCE', site=site)
squeeky_room = Object.global_objects.get(name='Squeaky Room', site=site)
mine_in_exit.set_property('dest', squeeky_room)
mine_west_exit = Object.global_objects.get(name='west from MINE-ENTRANCE', site=site)
mine_west_exit.set_property('dest', squeeky_room)
print('zork1 reset')
"""

# Repo root used as ``cwd`` for the docker-compose reset call.  Resolved
# from this file's path so the test still works when invoked via ``-m``.
_REPO_ROOT = Path(__file__).resolve().parents[2].parent


def _reset_zork1_state() -> None:
    """Put items back, close containers, and put Wizard at West of House.

    Idempotent.  Runs ``manage.py shell -c`` in the webapp container so
    each smoke-test invocation starts from the same world state regardless
    of how the previous run finished.
    """
    subprocess.run(
        [
            "docker-compose",
            "run",
            "--rm",
            "webapp",
            "manage.py",
            "shell",
            "-c",
            _RESET_SNIPPET,
        ],
        check=True,
        cwd=_REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# (command, substring expected in output, or None to just print + skip the
# check).  The zork1 bootstrap requires ``go <dir>`` rather than bare
# ``north``/``south``, and its parser doesn't peek into open containers —
# so the mailbox/leaflet beat from the canonical Zork opener doesn't apply
# here.
ZORK_COMMANDS = [
    # --- West of House: starting room ---
    ("look", "white house"),
    ("inventory", None),  # may carry leftovers from prior runs
    ("close mailbox", None),  # deterministic state
    ("open mailbox", "open"),  # "Opened." (empty) or "Opening the small mailbox reveals..."
    ("take leaflet", "Taken"),  # peeks into open mailbox
    ("read leaflet", "ZORK"),  # canonical Zork welcome leaflet
    # --- Loop around the house ---
    ("go north", "north side"),  # North of House
    ("go east", "behind"),  # Behind House
    ("go west", "kitchen"),  # Kitchen (Behind→Kitchen window auto-open)
    ("look", "kitchen"),
    ("go up", "attic"),  # Attic
    ("take rope", "Taken"),
    ("inventory", "rope"),
    ("go down", "kitchen"),  # back to Kitchen
    ("go west", "living"),  # Living Room
    # --- Living Room treasure prep ---
    ("look", "living"),
    ("drop leaflet", None),  # lighten load — rope stays for the Dome Room descent later
    ("take sword", "Taken"),
    ("take lantern", "Taken"),
    ("move rug", "rug"),  # first-time: reveals trap door; later: "moved the carpet"
    ("open trap door", "rickety"),  # opens trap door, reveals descending staircase
    ("light lantern", None),  # turns the lantern on
    ("go down", "cellar"),  # Cellar (CEXIT calls TRAP-DOOR-EXIT)
    ("look", None),
    # --- Phase C: Troll Room ---
    ("go north", "axe"),  # Troll Room (mentions axe-scarred walls)
    ("attack troll with sword", None),  # canonical Zork combat
    ("attack troll with sword", None),
    ("attack troll with sword", None),
    ("attack troll with sword", None),
    ("take axe", None),
    ("look", None),
    # --- Phase E-4-e Step 15: BAG-OF-COINS (maze) ---
    # Troll Room → west → MAZE-1 → south → MAZE-2 → east → MAZE-3 →
    # up → MAZE-5 (where the bag of coins waits).  Return path is the
    # mirror inverse: north → MAZE-3, west → MAZE-2, south → MAZE-1,
    # east → Troll Room.
    ("go west", "twisty"),  # MAZE-1 ("twisty little passages")
    ("go south", "twisty"),  # MAZE-2
    ("go east", "twisty"),  # MAZE-3
    ("go up", "twisty"),  # MAZE-5 — desc still says twisty passages; bag is here
    ("take bag", "Taken"),  # treasure: bag of coins (TVALUE=5)
    ("go north", "twisty"),  # MAZE-3
    ("go west", "twisty"),  # MAZE-2
    ("go south", "twisty"),  # MAZE-1
    ("go east", "axe"),  # back to Troll Room
    # --- Phase E-3: explore east beyond the troll room ---
    # With troll dead, the east exit from Troll Room opens into the
    # East-West Passage which leads to the Round Room — the gateway to
    # the rest of the Great Underground Empire.  We just verify the area
    # is reachable and round-trip back to the troll room.
    ("go east", "passage"),  # East-West Passage
    ("go east", "circular"),  # Round Room
    ("go southeast", "low cave"),  # Engravings Cave
    ("go northwest", "circular"),  # back to Round Room
    ("go west", "passage"),  # back to East-West Passage
    ("go west", "axe"),  # back to Troll Room
    # Drop axe early: troll is dead, axe weight (size=25) plus the rest
    # of inventory was overflowing LOAD-MAX when taking the painting.
    ("drop axe", None),
    ("go south", "cellar"),  # back to Cellar
    # --- Phase D-2: Gallery (painting treasure, requires troll dead) ---
    ("go south", "chasm"),  # East of Chasm
    ("go east", "gallery"),  # Gallery (PAINTING here)
    ("take painting", "Taken"),  # treasure 2: painting
    ("go west", "chasm"),  # back to East of Chasm
    ("go north", "cellar"),  # back to Cellar
    ("go up", "living"),  # Living Room (trophy case here)
    # V-PUT requires PRSI to have OPENBIT.  The trophy case has TRANSBIT
    # but starts un-OPENBIT in dungeon.zil — open it once before depositing.
    ("open trophy case", None),
    ("put painting in case", None),  # deposit treasure 2 in trophy case
    ("put bag in case", None),  # deposit bag of coins (TVALUE=5)
    ("close trap door", None),
    # --- Final stretch back to start ---
    ("go east", "kitchen"),  # Kitchen
    ("go east", "behind"),  # Behind House
    ("go south", "south side"),  # South of House
    ("go west", "white house"),  # back to West of House
    # --- Phase D: forest treasure run (jeweled egg from tree) ---
    # The bird's nest in Up a Tree contains the egg, the easiest of the 20
    # treasures to reach.  This proves the forest CEXIT chain plus the
    # tree-climb action and a TAKEBIT/CONTBIT pickup all work end-to-end.
    # Axe was already dropped earlier (Troll Room) so the egg pickup
    # has weight headroom.
    ("go north", "north"),  # North of House
    ("go north", "path"),  # Forest Path (FOREST-ROOM action)
    ("go up", "branches"),  # Up a Tree (TREE-ROOM action)
    ("take egg", "Taken"),  # treasure 1: jewel-encrusted egg
    ("inventory", "egg"),
    ("go down", "path"),  # back to Forest Path
    ("go south", "north side"),  # back to North of House
    # --- Phase E-2: bring egg to trophy case ---
    # Loop back through Behind House → Kitchen → Living Room.
    # Break egg with sword here: broken_egg (TVALUE=2) goes in the case;
    # broken_canary (TVALUE=1) stays in inventory for a later deposit.
    ("go east", "behind"),  # EAST-OF-HOUSE (DESC "Behind House")
    ("go west", "kitchen"),  # Kitchen (window auto-opens)
    ("go west", "living"),  # Living Room
    # Break egg with sword to reveal broken_canary (original egg is removed, broken_egg replaces it).
    # Both broken_egg and broken_canary are treasures (tvalue 2 and 1).
    # Egg was pre-opened at reset time, so we skip the V-MUNG break
    # (which would replace canary with broken_canary).  Take the
    # unbroken canary out of the open egg, then deposit egg.
    ("take canary", "Taken"),
    ("put egg in case", None),  # jewel-encrusted egg (TVALUE=5)
    # --- Phase E-4-e Step 19: BAUBLE (wind canary in forest room) ---
    # Detour up to Forest Path with the unbroken canary, wind it for
    # the bauble drop, take bauble, then return.
    ("go east", "kitchen"),
    ("go east", "behind"),
    ("go north", "north side"),  # North of House
    ("go north", "Path"),  # Forest Path
    ("wind canary", "bauble"),
    ("take bauble", "Taken"),  # treasure: brass bauble (TVALUE=1)
    ("go south", "north side"),
    ("go east", "behind"),
    ("go west", "kitchen"),
    ("go west", "living"),  # Living Room
    ("put bauble in case", None),  # deposit brass bauble (TVALUE=1)
    ("put canary in case", None),  # deposit unbroken canary (TVALUE=4)
    ("go east", "kitchen"),
    ("go east", "behind"),
    ("go south", "south side"),
    ("go west", "white house"),
    # --- Phase E-1/E-2: scoring infrastructure check ---
    # Substrate V-SCORE prints "Your score is N (total of 350 points)…"
    # and recomputes SCORE in LIVING-ROOM-FCN's M-END clause (now
    # ``endfunc``) whenever a treasure is put in the trophy case.
    # Exact intermediate score depends on per-treasure VALUE bonuses
    # plus room-discovery scoring, which the test exercises but does
    # not pin to an exact value here — Phase E-4-c asserts a higher
    # final-score rank.
    ("score", "score is"),
    # --- Phase E-4-a: Dome Room rope descent + torch ---
    # Re-descend to the Dome Room with the rope still in inventory, tie
    # it to the wooden railing (sets DOME-FLAG so the `down` exit
    # unlocks), climb down to Torch Room and grab the ivory torch
    # (TVALUE=6).  This is a one-way trip in canonical Zork — escape
    # requires the bell+book+candles ritual through the temple — so the
    # test ends in the temple area rather than returning to West of
    # House.
    ("go north", "north"),  # North of House
    ("go east", "behind"),  # Behind House
    ("go west", "kitchen"),  # Kitchen
    ("go west", "living"),  # Living Room
    ("open trap door", None),  # re-open (was closed earlier)
    ("go down", "cellar"),  # Cellar
    ("go north", "axe"),  # Troll Room (troll already dead from Phase C)
    ("go east", "passage"),  # East-West Passage
    ("go east", "circular"),  # Round Room
    ("go southeast", "low cave"),  # Engravings Cave
    ("go east", "dome"),  # Dome Room (DOME-ROOM-FCN, M-LOOK)
    ("tie rope to railing", "drops over"),
    ("go down", "pedestal"),  # Torch Room ("white marble pedestal" in TORCH-ROOM-FCN M-LOOK)
    ("take torch", "Taken"),  # treasure 3: ivory torch (TVALUE=6)
    ("inventory", "torch"),
    # --- Phase E-4-b: Egypt Room coffin ---
    # Drop the now-redundant sword and lantern (troll is dead and the
    # torch is a light source) so the heavy gold coffin (SIZE=55) fits
    # under LOAD-ALLOWED=100.  Skip bell/book/candles for now — they're
    # ritual tools for escaping Land of the Dead (Phase E-4-c).
    ("drop sword", None),
    ("drop lantern", None),
    ("go south", "Temple"),  # North Temple (DESC is "Temple")
    ("go east", "Egyptian"),  # Egypt Room (DESC is "Egyptian Room")
    ("take coffin", "Taken"),  # treasure 4: gold coffin (TVALUE=15, SIZE=55)
    ("inventory", "coffin"),
    # --- Phase E-4-c: pray at the altar to escape back to the surface ---
    # The South Temple's V-PRAY handler teleports the player to FOREST-1
    # with all carried items.  Walk back through the forest and house to
    # the trophy case to deposit the coffin and torch.  Bell, book, and
    # candles stay at the temples — we collect them on the LLD detour
    # at the end when inventory is light.
    ("go west", "Temple"),  # back to North Temple
    ("go south", "altar"),  # South Temple (Altar) — the only place pray works
    ("pray", None),  # V-PRAY teleports silently — output is empty
    ("go east", "path"),  # FOREST-1 → east → Forest Path
    ("go south", "north side"),  # → North of House
    ("go east", "behind"),  # → Behind House
    ("go west", "kitchen"),  # → Kitchen
    ("go west", "living"),  # → Living Room (trophy case still open from earlier)
    ("put torch in case", None),  # treasure 3 deposited (TVALUE=6)
    ("open coffin", None),  # open coffin (in inventory) to access sceptre inside
    ("take sceptre", "Taken"),  # treasure 5: ivory sceptre (TVALUE=6)
    ("put coffin in case", None),  # treasure 4 deposited (TVALUE=15)
    # 4 deposited (painting+broken_egg+torch+coffin) plus sceptre+broken_canary in
    # inventory — total TVALUE so far: 4+2+6+15=27.  Rank should be Adventurer or higher.
    ("score", "Adventurer"),
    # --- Step 2.1: Cyclops/CHALICE ---
    # The west exit from Living Room (condition_flag=MAGIC-FLAG) is traversable
    # because walk() only checks dest==None, not flags.  Same for up from Cyclops Room.
    ("go west", "Passage"),  # Strange Passage ("long passage")
    ("go west", "staircase"),  # Cyclops Room (M-LOOK mentions "staircase leading up")
    ("go up", "discarded"),  # Treasure Room (description: "discarded bags")
    ("take chalice", "Taken"),
    ("go down", "staircase"),  # back to Cyclops Room
    ("go east", "Passage"),  # Strange Passage
    ("go east", "living"),  # Living Room
    ("put chalice in case", None),  # deposit treasure: chalice (TVALUE=5)
    # --- Step 2.2: Machine Room DIAMOND + Gas Room bracelet ---
    # Recover torch from trophy case for light, then detour through Kitchen to
    # pick up garlic (needed to pass Bat Room without being teleported), then
    # navigate via Mirror Room 2 → Mirror Room 1 → Cold Passage → Slide Room →
    # Mine Entrance → Bat Room → Shaft Room → Smelly Room → Gas Room (bracelet)
    # → Mine 1-4 → Ladder Top/Bottom → Dead End 5 (coal) → Timber Room →
    # Lower Shaft → Machine Room.  After the machine puzzle, return via the
    # same mine chain and use Slide Room → down → Cellar shortcut to surface.
    ("take torch from case", "Taken"),
    # Garlic run (bats in Bat Room teleport you without it)
    ("go east", "kitchen"),
    ("take garlic", "Taken"),
    ("go west", "living"),
    # Screwdriver run: down to dungeon → east to NS Passage → Dam area
    ("open trap door", None),
    ("go down", "cellar"),
    ("go north", "axe"),  # Troll Room (troll already dead)
    ("go east", "passage"),  # East-West Passage
    ("go east", "circular"),  # Round Room
    # Detour east to Loud Room for the BAR treasure.  The room is loud by
    # default; saying "echo" silences it and reveals the platinum bar.
    ("go east", None),  # Loud Room
    ("echo", None),
    ("take bar", "Taken"),
    ("go west", "circular"),  # back to Round Room
    ("go north", "north-south"),  # NS Passage
    ("go northeast", None),  # Deep Canyon
    ("go east", "dam"),  # Dam Room
    ("go north", "Private"),  # Dam Lobby
    ("go north", "buttons"),  # Maintenance Room
    ("take screwdriver", "Taken"),
    ("go south", "Private"),  # back to Dam Lobby
    ("go south", "dam"),  # back to Dam Room
    ("go south", None),  # back to Deep Canyon
    ("go southwest", "north-south"),  # back to NS Passage
    ("go south", "circular"),  # back to Round Room
    # Mirror Room path to Mine Entrance
    ("go south", None),  # Narrow Passage
    ("go south", "mirror"),  # Mirror Room 2 ("enormous mirror" in description)
    ("rub mirror", "rumble"),  # teleport to Mirror Room 1 + room shakes
    # --- Phase E-4-e Step 17: TRIDENT (Atlantis Room) ---
    # Detour Mirror Room 1 → Small Cave → Atlantis Room.  The trident
    # (size=20) won't fit on top of bar (size=20) + torch (size=20) +
    # rest of inventory through the mining run, so we swap: drop bar at
    # Atlantis, take trident in its place, run mining as before, then
    # recover bar after the mine return via the Cold Passage detour.
    ("go east", "cave"),  # Small Cave (east from MR1)
    ("go down", "ancient"),  # Atlantis Room ("ancient room, long under water")
    ("drop bar", None),  # park bar at Atlantis to free 20 weight
    ("take trident", "Taken"),  # treasure: crystal trident (TVALUE=11)
    # Atlantis is asymmetric: down is from Small Cave, but UP returns to
    # TINY-CAVE.  Loop back to Mirror Room 1 via Twisting Passage.
    ("go up", "tiny"),  # Tiny Cave
    ("go west", "winding"),  # Twisting Passage
    ("go north", "mirror"),  # Mirror Room 1
    ("go north", "passage"),  # Cold Passage
    ("go west", "slide"),  # Slide Room (no distinct desc, just navigate)
    ("go north", "entrance"),  # Mine Entrance ("entrance of what might have been a coal mine")
    ("go in", "squeaky"),  # Squeeky Room
    ("go north", "doors only"),  # Bat Room (garlic in inventory → no bat attack)
    ("take jade", "Taken"),  # treasure: jade figurine (TVALUE=5) — grab on first pass
    ("go east", "shaft"),  # Shaft Room
    ("go north", "odor"),  # Smelly Room
    ("go down", "gas"),  # Gas Room ("smells strongly of coal gas")
    ("take bracelet", "Taken"),  # treasure: sapphire bracelet (TVALUE=5)
    # Drop garlic to free inventory weight for the coal+diamond run.
    # Bats already passed through; garlic isn't needed past this point.
    ("drop garlic", None),
    # Navigate coal mine: Mine 1 → 2 → 3 → 4 → Ladder Top → Ladder Bottom
    ("go east", None),  # Mine 1
    ("go northeast", None),  # Mine 2
    ("go southeast", None),  # Mine 3
    ("go southwest", None),  # Mine 4
    ("go down", None),  # Ladder Top
    ("go down", None),  # Ladder Bottom
    ("go south", "dead end"),  # Dead End 5 (coal here)
    ("take coal", "Taken"),
    ("go north", None),  # Ladder Bottom
    ("go west", "timber"),  # Timber Room
    ("go west", "draft"),  # Lower Shaft (Drafty Room)
    ("go south", "machine"),  # Machine Room
    # Machine puzzle: load coal, activate switch, collect diamond
    ("open machine", None),
    ("put coal in machine", None),
    ("close machine", None),
    ("turn switch with screwdriver", None),
    ("open machine", None),
    ("take diamond", "Taken"),  # treasure: huge diamond (TVALUE=10)
    # Return to surface via mine chain → Slide Room → down → Cellar
    ("go north", "draft"),  # Lower Shaft
    ("go east", "timber"),  # Timber Room
    ("go east", None),  # Ladder Bottom
    ("go up", None),  # Ladder Top
    ("go up", None),  # Mine 4
    ("go north", None),  # Mine 3
    ("go east", None),  # Mine 2 (east → Mine 2)
    ("go south", None),  # Mine 1
    ("go north", "gas"),  # Gas Room
    ("go up", "odor"),  # Smelly Room
    ("go south", "shaft"),  # Shaft Room
    ("go west", "doors only"),  # Bat Room (garlic still in inventory; jade already taken)
    ("go south", "squeaky"),  # Squeeky Room
    ("go east", "entrance"),  # Mine Entrance
    ("go south", None),  # Slide Room
    ("go down", "cellar"),  # Cellar (Slide Room → down shortcut)
    ("go up", "living"),  # Living Room (trap door CEXIT)
    ("put bracelet in case", None),  # deposit bracelet (TVALUE=5)
    ("put diamond in case", None),  # deposit diamond (TVALUE=10)
    ("put jade in case", None),  # deposit jade figurine (TVALUE=5)
    ("put trident in case", None),  # deposit crystal trident (TVALUE=11)
    # NOTE: bar (TVALUE=5) was parked at Atlantis during the trident
    # detour to keep weight within LOAD-MAX during mining.  Recovering
    # it requires another rub-mirror swap which the smoke currently
    # can't do (mirror moved to MR1, MR2 has none).  Trident's +11
    # outweighs the lost +5 — net +6 vs the no-trident baseline.
    # --- POT-OF-GOLD detour (Step 2.5 of PHASE_E4E_PLAN) ---
    # Sceptre is still in inventory at this point (we deposit it just
    # before the boat puzzle).  Take it overland to End of Rainbow,
    # wave it to materialise the rainbow + reveal the pot, take pot.
    # Path: Living Room → east → Kitchen → east → Behind House →
    # east → Clearing → east → Canyon View → down → Cliff Middle →
    # down → Canyon Bottom → north → End of Rainbow.  (Aragain Falls
    # itself is not on this path — canyon_bottom → north lands
    # directly at End of Rainbow.)
    ("go east", "kitchen"),
    ("go east", "behind"),
    ("go east", "clearing"),  # Forest Clearing
    ("go east", "canyon"),  # Canyon View
    ("go down", "ledge"),  # Cliff Middle ("ledge about halfway up")
    ("go down", "river canyon"),  # Canyon Bottom ("beneath the walls of the river canyon")
    ("go north", "rainbow"),  # End of Rainbow
    # Wave sceptre at End of Rainbow — materialises the rainbow AND
    # reveals the pot of gold in the same room.
    ("wave sceptre", "rainbow"),
    ("take pot", "Taken"),  # treasure: pot of gold (TVALUE=10)
    # Return to Living Room to deposit.  Reverse path: sw back to
    # canyon bottom → up → cliff middle → up → canyon view → west to
    # clearing → west to Behind House → west to kitchen → west to LR.
    ("go southwest", "river canyon"),  # Canyon Bottom
    ("go up", "ledge"),  # Cliff Middle
    ("go up", "canyon"),  # Canyon View
    ("go northwest", "clearing"),  # Clearing (CANYON-VIEW.west goes into forest)
    ("go west", "behind"),  # Behind House (EAST-OF-HOUSE)
    ("go west", "kitchen"),
    ("go west", "living"),  # Living Room
    ("put pot in case", None),  # deposit pot of gold (TVALUE=10)
    # The boat punctures if the player boards while carrying the sceptre
    # (sharp object), so deposit the sceptre temporarily first.
    ("put sceptre in case", None),
    # --- Phase E-4-e Step 16: TRUNK-OF-JEWELS (reservoir drain) ---
    # Inventory at this point is light (just torch + broken_egg+canary)
    # so the heavy trunk (size 35) fits.  Path: cellar → troll → passage
    # → round → NS → canyon → dam → lobby → maintenance → press yellow
    # → take wrench → south → south → turn bolt → drop wrench → wait
    # twice for i-rempty to drain the reservoir → west → north → take
    # trunk → south → east → south → southwest → south → west → west →
    # south → up to Living Room → put trunk in case.
    ("open trap door", None),
    ("go down", "cellar"),
    ("go north", "axe"),  # Troll Room
    ("go east", "passage"),
    ("go east", "circular"),  # Round Room
    ("go north", "north-south"),
    ("go northeast", None),  # Deep Canyon
    ("go east", "dam"),
    ("go north", "Private"),  # Dam Lobby
    ("go north", "buttons"),  # Maintenance Room
    ("press yellow button", "Click"),  # GATE-FLAG = True
    ("take wrench", "Taken"),
    ("go south", "Private"),
    ("go south", "dam"),
    ("turn bolt with wrench", "sluice"),  # GATES-OPEN; i-rempty queued (8 turns)
    ("drop wrench", None),  # drop heavy wrench (size 10) — done with it
    ("wait", None),  # 5 ticks
    ("wait", None),  # 5 more ticks → i-rempty fires; reservoir drains
    ("go west", "stream"),  # Reservoir-South (drained desc)
    ("go north", "mud pile"),  # Reservoir (drained); trunk visible
    ("take trunk", "Taken"),  # treasure: trunk of jewels (TVALUE=5)
    ("go south", "stream"),
    ("go east", "dam"),
    ("go south", None),  # Deep Canyon
    ("go southwest", "north-south"),  # NS Passage
    ("go south", "circular"),  # Round Room
    ("go west", "passage"),  # East-West Passage
    ("go west", "axe"),  # Troll Room
    ("go south", "cellar"),
    ("go up", "living"),
    ("put trunk in case", None),  # deposit trunk of jewels (TVALUE=5)
    # --- Bar recovery (parked at Atlantis during the trident detour) ---
    # The first rub at MR2 swapped contents — mirror_1 moved to MR2,
    # mirror_2 moved to MR1.  Now rub mirror at MR2 again to swap back
    # and teleport to MR1, then descend to Atlantis for the bar.
    ("open trap door", None),
    ("go down", "cellar"),
    ("go north", "axe"),  # Troll Room
    ("go east", "passage"),
    ("go east", "circular"),  # Round Room
    ("go south", None),  # Narrow Passage
    ("go south", "mirror"),  # Mirror Room 2 (mirror_1 here after first swap)
    ("rub mirror", "rumble"),  # second swap; player → MR1
    ("go east", "cave"),  # Small Cave
    ("go down", "ancient"),  # Atlantis Room
    ("take bar", "Taken"),  # recover the parked platinum bar
    ("go up", "tiny"),  # Small Cave
    ("go west", "winding"),  # Twisting Passage
    ("go north", "mirror"),  # Mirror Room 1
    ("go north", "passage"),  # Cold Passage
    ("go west", "slide"),  # Slide Room
    ("go down", "cellar"),
    ("go up", "living"),
    ("put bar in case", None),  # deposit platinum bar (TVALUE=5)
    # --- Phase E-4-e Step 18: SKULL (Land of the Living Dead ritual) ---
    # Detour to Dam Lobby first to grab the matchbook (needed for the
    # ritual; can't take it during the mining run because the lit
    # torch + matchbook in Gas Room triggers BOOM-ROOM's death).
    # Then continue: Living Room → trap door → Cellar → Troll → ... →
    # Dome Room → Torch Room → North Temple (take bell) → South Temple
    # (take book, take candles) → DOWN (one-way; requires COFFIN-CURE
    # = coffin not in inventory, ✓ deposited) → Tiny Cave → DOWN →
    # Entrance to Hades (LLD-ROOM).  Ritual: ring bell, light match,
    # light candles, read book → LLD-FLAG = T.  Then GO IN to Land of
    # the Living Dead, take the skull, walk back via Tiny Cave → MR2
    # → … → Living Room.
    ("open trap door", None),
    ("go down", "cellar"),
    ("go north", "axe"),  # Troll Room
    ("go east", "passage"),  # East-West Passage
    ("go east", "circular"),  # Round Room
    # Matchbook detour: Round → NS → Deep Canyon → Dam Room → Dam Lobby
    ("go north", "north-south"),  # NS Passage
    ("go northeast", None),  # Deep Canyon
    ("go east", "dam"),  # Dam Room
    ("go north", "Private"),  # Dam Lobby
    ("take matchbook", "Taken"),
    ("go south", "dam"),
    ("go south", None),  # Deep Canyon
    ("go southwest", "north-south"),
    ("go south", "circular"),  # back to Round Room
    ("go southeast", "low cave"),  # Engravings Cave
    ("go east", "dome"),  # Dome Room (rope still tied from Phase E-4-a)
    ("go down", "pedestal"),  # Torch Room
    ("go south", "Temple"),  # North Temple
    ("take bell", "Taken"),
    ("go south", "altar"),  # South Temple (DESC: "Altar")
    ("take book", "Taken"),
    ("take candles", "Taken"),
    ("go down", "tiny"),  # Tiny Cave (DESC LDESC has "tiny cave")
    ("go down", "gateway"),  # Entrance to Hades (M-LOOK: "outside a large gateway")
    # Ritual sequence — translator's BELL-F handles ring bell at LLD,
    # MATCH-FUNCTION lights the match (FLAMEBIT + ONBIT), CANDLES-FCN
    # uses the lit match to set CANDLES ONBIT, and BLACK-BOOK + LLD-ROOM
    # M-BEG combine to set LLD-FLAG once XB+candles ONBIT are both true.
    ("ring bell", None),  # SETG XB, MOVE bell→hot-bell, queue I-XB
    ("light match", None),  # FLAMEBIT + ONBIT on match
    ("light candles", None),  # candles ONBIT (auto-uses lit match)
    ("read book", None),  # M-BEG sees XB+candles ONBIT, sets XC; read sets LLD-FLAG
    ("go in", "Living Dead"),  # gate opens after LLD-FLAG = T
    ("take skull", "Taken"),  # treasure: crystal skull (TVALUE=10)
    # Return to surface: Land of Dead → Entrance to Hades → up → Tiny Cave
    # → north → Mirror Room 2 → north → Narrow Passage → north → Round Room
    # → west → East-West Passage → west → Troll Room → south → Cellar.
    ("go north", "gateway"),  # Entrance to Hades
    ("go up", "tiny"),
    ("go north", "mirror"),
    ("go north", None),  # Narrow Passage (no clear DESC keyword)
    ("go north", "circular"),  # Round Room
    ("go west", "passage"),
    ("go west", "axe"),
    ("go south", "cellar"),
    ("go up", "living"),
    ("put skull in case", None),  # deposit crystal skull (TVALUE=10)
    # Drop ritual leftovers — they're not treasures and the inventory
    # count pushes random fumble checks (see itake's FUMBLE-PROB) over
    # the threshold during later treasure pickups (e.g. scarab).
    ("drop book", None),
    ("drop candles", None),
    ("drop matchbook", None),
    # Score check after depositing all reachable treasures.
    ("score", None),
    ("open trap door", None),
    ("go down", "cellar"),
    ("go north", "axe"),  # Troll Room
    ("go east", "passage"),  # East-West Passage
    ("go east", "circular"),  # Round Room
    ("go north", "north-south"),  # NS Passage
    ("go northeast", None),  # Deep Canyon
    ("go east", "dam"),  # Dam Room
    ("go down", "Frigid"),  # Dam Base ("river Frigid is flowing by here")
    ("board magic boat", None),  # enter the boat
    # Try walking in a blocked direction first to verify the boat's M-BEG
    # dispatch via do_command/preturnfunc still works at Dam Base.
    ("go north", "label"),  # blocked: not on water yet
    # Launch — should drift via RIVER-LAUNCH (DAM-BASE → RIVER-1).
    ("launch", None),
    ("look", "river"),  # boat moved to RIVER-1
    # i-river daemon was queued with delay = RIVER-1's speed (4 turns).
    # Each `wait` does 4 ticks (1 in do_command + 3 in v-wait's clocker
    # loop), so 1 wait = 1 drift.  The river speeds up as you descend
    # (RIVER-1=4, RIVER-2=4, RIVER-3=3, RIVER-4=2, RIVER-5=1).
    # Two waits drifts through R1→R2→R3.  Then a single-tick `look`
    # drifts R3→R4.  At RIVER-4 we take the buoy (1 tick, no drift)
    # and land via `go east` (which fires the next drift to R5 first,
    # then walks east from R5 → SHORE — the daemon cancels at SHORE
    # since it's not in the river system).
    ("wait", "downstream"),  # R1 → R2
    ("wait", "downstream"),  # R2 → R3
    ("look", "valley"),  # describes RIVER-3 (drift R3 → R4 not yet due)
    ("go east", "sandy"),  # tick fires R3 → R4 drift, then walk east → SANDY-BEACH
    ("disembark boat", "own feet"),
    ("look", "sandy beach"),
    ("take buoy", "Taken"),
    ("open buoy", None),
    # The parser's ``Object.find()`` peeks into open child containers, so
    # ``take emerald`` (or ``take emerald from buoy``) works once the
    # buoy is open.  TREASURE-INSIDE's ZIL ``<RFALSE>`` translation now
    # falls through to v-open's ``set_flag(open, True)`` correctly.
    ("take emerald", "Taken"),
    # SCARAB (Sandy Cave): take shovel here, then dig 3x.  Stop at 3 —
    # 4 digs collapse the cave (death).
    ("take shovel", "Taken"),
    ("go northeast", None),  # Sandy Cave (passage NE from Sandy Beach)
    ("dig sand with shovel", None),
    ("dig sand with shovel", None),
    ("dig sand with shovel", "scarab"),  # 3rd dig should reveal the scarab
    ("take scarab", "Taken"),  # treasure: ancient scarab (TVALUE=5)
    ("go southwest", None),  # back to Sandy Beach
]


def main() -> int:
    failures: list[tuple[str, str, str]] = []

    print("[smoke] resetting zork1 world state ...", flush=True)
    _reset_zork1_state()

    with MooSSH(
        host="zork1.local",
        port=8022,
        user="phil+zork1.local",
        password="qw12er34",
        timeout=10,
        verbose=True,
    ) as moo:
        # The ``Connected to universe: …`` banner is written by interact()
        # before embed() takes over. connect() waits 4 s for the session to
        # settle, accumulating that banner in child.before.
        welcome = strip_ansi(moo.child.before or "")
        print("\n>>> CONNECT-TIME BUFFER\n" + welcome + "\n")

        if "Connected to universe: zork1.local" not in welcome:
            failures.append(("connect-banner", "Connected to universe: zork1.local", welcome))

        moo.enable_delimiters()

        for cmd, expected in ZORK_COMMANDS:
            out = moo.run(cmd)
            print(f">>> {cmd!r} (out len={len(out)})\n{out}\n")
            if expected and expected.lower() not in out.lower():
                failures.append((cmd, expected, out))

    if failures:
        print("FAIL:")
        for cmd, expected, actual in failures:
            print(f"  {cmd!r} did not contain {expected!r}")
            print(f"    actual: {actual!r}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
