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
altar = Object.global_objects.get(name='altar', site=site)
book = Object.global_objects.get(name='black book', site=site)
candles = Object.global_objects.get(name='pair of candles', site=site)
egypt = Object.global_objects.get(name='Egyptian Room', site=site)
coffin = Object.global_objects.get(name='gold coffin', site=site)
case = Object.global_objects.get(name='trophy case', site=site)
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
coffin.location = egypt; coffin.save()
mailbox.set_property('open', False); mailbox.save()
trap.set_property('open', False); trap.save()
case.set_property('open', False); case.save()
wiz.set_property('zstate_rug_moved', False)
wiz.set_property('zstate_score', 0)
wiz.set_property('zstate_base_score', 0)
wiz.set_property('zstate_dome_flag', False)
wiz.location = woh; wiz.save()
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
    # Drop the axe first — with sword + lantern + painting already in hand,
    # the load is at limit and the egg won't fit otherwise.
    ("drop axe", None),
    ("go north", "north"),  # North of House
    ("go north", "path"),  # Forest Path (FOREST-ROOM action)
    ("go up", "branches"),  # Up a Tree (TREE-ROOM action)
    ("take egg", "Taken"),  # treasure 1: jewel-encrusted egg
    ("inventory", "egg"),
    ("go down", "path"),  # back to Forest Path
    ("go south", "north side"),  # back to North of House
    # --- Phase E-2: bring egg to trophy case (second treasure) ---
    # Loop back through Behind House → Kitchen → Living Room with egg in
    # hand to deposit treasure 2.  Egg's TVALUE is 5, on top of painting's
    # 4, so post-deposit score should be 9.
    ("go east", "behind"),  # EAST-OF-HOUSE (DESC "Behind House")
    ("go west", "kitchen"),  # Kitchen (window auto-opens)
    ("go west", "living"),  # Living Room
    ("put egg in case", None),
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
    # the trophy case to deposit the coffin and torch.
    ("go west", "Temple"),  # back to North Temple
    ("go south", "altar"),  # South Temple (Altar) — the only place pray works
    ("pray", None),  # V-PRAY teleports silently — output is empty
    ("go east", "path"),  # FOREST-1 → east → Forest Path
    ("go south", "north side"),  # → North of House
    ("go east", "behind"),  # → Behind House
    ("go west", "kitchen"),  # → Kitchen
    ("go west", "living"),  # → Living Room (trophy case still open from earlier)
    ("put torch in case", None),  # treasure 3 deposited (TVALUE=6)
    ("put coffin in case", None),  # treasure 4 deposited (TVALUE=15)
    # 4 treasures (painting+egg+torch+coffin) deposited plus room-discovery
    # bonuses pushes score above 50 — rank "Novice Adventurer" or higher.
    ("score", "Adventurer"),
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
