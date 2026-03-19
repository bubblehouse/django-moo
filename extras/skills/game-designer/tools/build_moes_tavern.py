#!/usr/bin/env python3
"""
build_moes_tavern.py - Build the Moe's Tavern environment in DjangoMOO.

Executes all wizard commands to create the 5-room Simpsons-themed environment:
rooms, exits, objects, NPCs, and interactive verbs.

Run from the django-moo project root:
    python extras/skills/game-designer/tools/build_moes_tavern.py

Requires:
    pip install pexpect
    DjangoMOO running locally (docker-compose up)

To verify after running:
    SSH in as Wizard and run: @test-moes-tavern
    Or check docker logs: docker logs django-moo-shell-1 | tail -100
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from moo_ssh import MooSSH  # pylint: disable=wrong-import-position


def obj_id(output):
    """Extract #N from @create output like 'Created #34 (bar stool)'."""
    m = re.search(r"(#\d+)", output)
    return m.group(1) if m else None


def create(moo, name, parent="$thing"):
    """Create an object and return its #N reference."""
    output = moo.run(f'@create "{name}" from "{parent}"')
    ref = obj_id(output)
    if not ref:
        print(f"  WARNING: could not get ID for '{name}' from: {output!r}", file=sys.stderr)
    return ref


def describe(moo, ref, desc):
    """Describe an object by #N reference (unambiguous)."""
    moo.run(f'@describe {ref} as "{desc}"')


def set_verb(moo, verb_name, obj_ref, code):
    """
    Create or update a verb using @edit ... with, passing multi-line code as
    a single \\n-escaped string. The @edit verb unescapes \\n back to newlines.

    obj_ref may be a #N id (not quoted) or a plain name (quoted).
    """
    # Escape backslashes first, then newlines, then double-quotes
    escaped = code.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    # #N refs are unquoted; plain names are quoted
    if str(obj_ref).startswith("#"):
        moo.run(f'@edit verb {verb_name} on {obj_ref} with "{escaped}"')
    else:
        moo.run(f'@edit verb {verb_name} on "{obj_ref}" with "{escaped}"')


# ---------------------------------------------------------------------------
# Phase 1: Rooms and exits
# ---------------------------------------------------------------------------
# All room describes use "@describe here" which is always unambiguous.
#
# Room structure:
#   The Laboratory
#       south -> Moe's Tavern - Main Bar
#                   east  -> Moe's Tavern - Men's Room
#                   west  -> Moe's Tavern - Ladies Room
#                   north -> Moe's Tavern - Back Room
#                                north -> Moe's Tavern - Secret Room (locked)

ROOMS = [
    '@dig south to "Moe\'s Tavern - Main Bar"',
    "south",
    '@describe here as "Dark, smoky dive bar with a worn wooden bar counter, cracked bar stools, a battered pool table, a vintage jukebox, an old rotary pay phone, a small TV, and a Love Tester machine. The floor is sticky with spilled beer and the whole place smells like decades of despair and cheap booze."',
    "@dig east to \"Moe's Tavern - Men's Room\"",
    "east",
    "@describe here as \"Grimy single-stall bathroom with a broken lock on the door. The cracked mirror reflects your shame, the toilet has seen better days, and you're not sure what's growing in the corners. Best not to touch anything.\"",
    '@tunnel west to "Moe\'s Tavern - Main Bar"',
    "west",
    '@dig west to "Moe\'s Tavern - Ladies Room"',
    "west",
    "@describe here as \"Former ladies room converted into Moe's office after no female patrons since 1979. A toilet serves as an improvised desk chair in front of a cluttered desk. Boxing posters from Moe's fighting days cover the walls, and a tampon dispenser has been repurposed to hold cigars.\"",
    '@tunnel east to "Moe\'s Tavern - Main Bar"',
    "east",
    '@dig north to "Moe\'s Tavern - Back Room"',
    "north",
    '@describe here as "Cluttered storage area filled with beer kegs, cardboard boxes of bar supplies, and various items of questionable legality. Moe\'s shotgun leans against the wall for security. A shady-looking door in the back wall is locked tight."',
    '@tunnel south to "Moe\'s Tavern - Main Bar"',
    '@dig north to "Moe\'s Tavern - Secret Room"',
    "north",
    '@describe here as "A dimly lit room with bare concrete walls. Several abandoned animal cages line the walls, their doors hanging open. The air is musty and you probably don\'t want to know what this room was used for."',
    '@tunnel south to "Moe\'s Tavern - Back Room"',
    "south",
    "south",
    # Back in Main Bar; add reverse exit to Lab
    '@tunnel north to "The Laboratory"',
]


# ---------------------------------------------------------------------------
# Phases 2-6: Objects (dynamic, use #N to avoid ambiguity on duplicates)
# ---------------------------------------------------------------------------


def build_main_bar_objects(moo):
    moo.run("look")

    ref = create(moo, "bar counter")
    describe(
        moo,
        ref,
        "Worn wooden bar counter, scarred with decades of spilled beer and cigarette burns. Behind it, bottles of questionable spirits are arranged in no particular order.",
    )

    ref = create(moo, "bar stool")
    describe(moo, ref, "Wobbly bar stool with cracked red vinyl padding. At least three of its four legs are reliable.")
    create(moo, "bar stool")
    create(moo, "bar stool")
    create(moo, "bar stool")

    ref = create(moo, "pool table")
    describe(
        moo,
        ref,
        "Battered pool table with faded green felt, missing the 8-ball. A handwritten sign reads 'No hustling. -Moe'",
    )

    ref = create(moo, "pool cue")
    describe(moo, ref, "Wooden pool cue with a chipped tip, leaning against the wall.")

    ref = create(moo, "jukebox")
    describe(moo, ref, "Vintage jukebox glowing with warm neon light. The song list is entirely depressing country.")

    ref = create(moo, "wall phone")
    describe(moo, ref, "Old rotary pay phone on the wall, its receiver worn smooth by thousands of prank calls.")

    ref = create(moo, "TV")
    describe(moo, ref, "Small CRT television mounted in the corner, usually showing sports or news nobody is watching.")

    ref = create(moo, "love tester")
    describe(
        moo,
        ref,
        "Vintage Love Tester machine with a grip handle and a meter labeled Cold Fish through Nuclear Meltdown.",
    )

    ref = create(moo, "peanuts")
    describe(moo, ref, "Bowl of stale peanuts that have probably been here since the bar opened.")

    duff_ref = create(moo, "Duff beer")
    describe(moo, duff_ref, "Cold can of Duff beer, Springfield's favorite beverage.")
    create(moo, "Duff beer")
    create(moo, "Duff beer")
    create(moo, "Duff beer")
    return duff_ref


def build_mens_room_objects(moo):
    moo.run("east")

    ref = create(moo, "toilet")
    describe(moo, ref, "Grimy toilet that's seen better days. The flush handle is unreliable at best.")

    ref = create(moo, "sink")
    describe(moo, ref, "Cracked porcelain sink with a rusty faucet. The hot and cold labels are reversed.")

    ref = create(moo, "mirror")
    describe(moo, ref, "Cracked mirror covered in mysterious stains. It reflects your shame accurately.")

    ref = create(moo, "broken lock")
    describe(moo, ref, "Door lock that never quite works right. Someone has written 'Knock first' in marker.")

    moo.run("west")


def build_ladies_room_objects(moo):
    moo.run("west")

    ref = create(moo, "toilet")
    describe(
        moo, ref, "Old toilet repurposed as an office chair, positioned in front of the desk. Surprisingly comfortable."
    )

    ref = create(moo, "desk")
    describe(moo, ref, "Cluttered desk covered with papers, old racing forms, and an overflowing ashtray.")

    ref = create(moo, "boxing poster")
    describe(
        moo, ref, "Faded poster from one of Moe's amateur boxing matches. 'The Mangler' appears to have won that one."
    )
    create(moo, "boxing poster")

    ref = create(moo, "tampon dispenser")
    describe(moo, ref, "Vintage tampon dispenser mounted on the wall, repurposed to dispense cigars instead.")

    moo.run("east")


def build_back_room_objects(moo):
    moo.run("north")

    ref = create(moo, "beer keg")
    describe(moo, ref, "Large steel keg of Duff beer, one of several stacked here.")
    create(moo, "beer keg")
    create(moo, "beer keg")

    ref = create(moo, "supply boxes")
    describe(moo, ref, "Cardboard boxes filled with bar supplies and mystery items. Some are unlabeled.")

    ref = create(moo, "Moe's shotgun")
    describe(moo, ref, "Moe's trusty shotgun, kept here for security. The safety appears to be off.")

    ref = create(moo, "shady door")
    describe(
        moo,
        ref,
        "A heavy door with multiple padlocks and a hand-lettered sign: PRIVATE - KEEP OUT. The door leads north.",
    )

    moo.run("south")


def build_secret_room_objects(moo):
    moo.run("north")
    moo.run("north")

    ref = create(moo, "animal cages")
    describe(
        moo,
        ref,
        "Several rusted animal cages of various sizes, their doors hanging open ominously. Best not to speculate.",
    )

    moo.run("south")
    moo.run("south")


def build_npcs(moo):
    ref = create(moo, "Moe Szyslak", "$player")
    describe(
        moo,
        ref,
        "Surly bartender with a gravelly voice, perpetually grumpy expression, and a face like a dropped pizza.",
    )

    ref = create(moo, "Barney Gumble", "$player")
    describe(moo, ref, "Disheveled regular with perpetual five o'clock shadow, swaying slightly on his stool.")

    ref = create(moo, "Homer Simpson", "$player")
    describe(moo, ref, "Overweight man in white shirt and blue pants, staring contentedly at the TV or a Duff beer.")


# ---------------------------------------------------------------------------
# Phase 8: Interactive verbs (multi-line Python, via editor)
# ---------------------------------------------------------------------------
VERBS = [
    {
        "verb": "call",
        "obj": "wall phone",
        "code": (
            "from moo.sdk import context\n"
            "\n"
            'name = context.parser.get_dobj_str() if context.parser.has_dobj_str() else ""\n'
            "prank_names = [\n"
            '    "seymour butts", "i.p. freely", "jacques strap",\n'
            '    "hugh jass", "amanda hugginkiss", "ivana tinkle",\n'
            "]\n"
            "\n"
            "if name.lower() in prank_names:\n"
            '    print("You dial the phone...")\n'
            '    this.location.announce("The phone rings. Moe picks it up.")\n'
            "    this.location.announce('Moe: \"Moe\\'s Tavern, Moe speaking.\"')\n"
            "    this.location.announce(f'Moe: \"Is there a {name.title()} here? Hey everybody, I need {name.title()}!\"')\n"
            '    this.location.announce("*Laughter erupts from the bar*")\n'
            "    this.location.announce('Moe: \"Why you little! If I ever catch you...\"')\n"
            '    this.location.announce("*Moe slams down the phone*")\n'
            "else:\n"
            '    print("You dial the phone, but nobody answers.")\n'
        ),
    },
    {
        "verb": "drink",
        "obj": "Duff beer",
        "code": (
            "from moo.sdk import context\n"
            "\n"
            'print("You take a long swig of ice-cold Duff beer.")\n'
            'print("Ahhhh... refreshing!")\n'
            'this.location.announce(f"{context.player.name} drinks a Duff beer with satisfaction.")\n'
            "this.delete()\n"
        ),
    },
    {
        "verb": "play",
        "obj": "pool table",
        "code": (
            "from moo.sdk import context\n"
            "\n"
            'print("You rack up the balls and grab a cue.")\n'
            'print("You line up a shot and... scratch! The cue ball drops right into the pocket.")\n'
            'this.location.announce(f"{context.player.name} attempts to play pool but scratches immediately.")\n'
        ),
    },
    {
        "verb": "play",
        "obj": "jukebox",
        "code": (
            "from moo.sdk import context\n"
            "import time\n"
            "\n"
            "songs = [\n"
            '    "Stand By Your Man",\n'
            '    "I\'m So Lonesome I Could Cry",\n'
            '    "She Thinks My Tractor\'s Sexy",\n'
            '    "The Chair",\n'
            '    "A Boy Named Sue",\n'
            "]\n"
            "song = songs[int(time.time()) % len(songs)]\n"
            'print("You drop a quarter in the jukebox.")\n'
            'print(f"The jukebox begins playing \\"{song}\\"")\n'
            'this.location.announce(f"The jukebox plays \\"{song}\\" - a melancholy tune fills the bar.")\n'
        ),
    },
    {
        "verb": "test",
        "obj": "love tester",
        "code": (
            "from moo.sdk import context\n"
            "import time\n"
            "\n"
            'ratings = ["Cold Fish", "Warm", "Hot Stuff", "Burning Love", "Nuclear Meltdown"]\n'
            "rating = ratings[int(time.time()) % len(ratings)]\n"
            'print("You grab the handle and the needle starts to spin...")\n'
            'print(f"*DING!* The meter reads: {rating}!")\n'
            'this.location.announce(f"{context.player.name} uses the Love Tester. Rating: {rating}!")\n'
        ),
    },
    {
        "verb": "use",
        "obj": "love tester",
        "code": ('this.get_verb("test")()\n'),
    },
    {
        "verb": "use",
        "obj": "tampon dispenser",
        "code": (
            "from moo.sdk import context, create, lookup\n"
            "\n"
            'print("You turn the dial on the tampon dispenser...")\n'
            'print("*CLUNK* A cigar drops out instead!")\n'
            'this.location.announce(f"{context.player.name} gets a cigar from the repurposed tampon dispenser.")\n'
            "system = lookup(1)\n"
            'cigar = create("cigar", parents=[system.thing], location=context.player)\n'
            'cigar.set_property("description", "A cheap cigar that smells vaguely of vanilla and regret.")\n'
            'print("*A cigar appears in your inventory*")\n'
        ),
    },
    {
        "verb": "order",
        "obj": "Moe Szyslak",
        "code": (
            "from moo.sdk import context, create, lookup\n"
            "\n"
            'beverage = context.parser.get_dobj_str() if context.parser.has_dobj_str() else "beer"\n'
            "\n"
            'if "beer" in beverage.lower() or "duff" in beverage.lower():\n'
            "    print(\"Moe: 'One Duff, comin' right up.'\")\n"
            '    this.location.announce(f"Moe slides a Duff beer down the bar to {context.player.name}.")\n'
            "    system = lookup(1)\n"
            '    beer = create("Duff beer", parents=[system.thing], location=context.player)\n'
            '    beer.set_property("description", "Cold can of Duff beer, Springfield\'s favorite beverage.")\n'
            '    print("*A cold Duff beer appears in your inventory*")\n'
            "else:\n"
            "    print(\"Moe: 'We got Duff, Duff Lite, or Duff Dry. Take yer pick.'\")\n"
        ),
    },
    {
        "verb": "talk",
        "obj": "Barney Gumble",
        "code": (
            "from moo.sdk import context\n"
            "import time\n"
            "\n"
            "responses = [\n"
            '    "*BURRRP*",\n'
            '    "I love you, man... *hic*",\n'
            '    "Heyyy buddy... got a quarter?",\n'
            '    "Moe! Another round!",\n'
            '    "*Barney sways gently on his stool*",\n'
            "]\n"
            "print(f\"Barney: '{responses[int(time.time()) % len(responses)]}'\")\n"
        ),
    },
    {
        "verb": "greet",
        "obj": "Barney Gumble",
        "code": ('this.get_verb("talk")()\n'),
    },
    {
        "verb": "talk",
        "obj": "Homer Simpson",
        "code": (
            "from moo.sdk import context\n"
            "import time\n"
            "\n"
            "responses = [\n"
            '    "D\'oh!",\n'
            '    "Mmmm... beer...",\n'
            '    "Moe, gimme another Duff!",\n'
            '    "Why you little...!",\n'
            '    "Woo-hoo!",\n'
            "]\n"
            "print(f\"Homer: '{responses[int(time.time()) % len(responses)]}'\")\n"
        ),
    },
    {
        "verb": "greet",
        "obj": "Homer Simpson",
        "code": ('this.get_verb("talk")()\n'),
    },
    {
        "verb": "order",
        "obj": "Moe's Tavern - Main Bar",
        "code": (
            "from moo.sdk import context, create, lookup\n"
            "\n"
            "moe = None\n"
            "for obj in this.contents.all():\n"
            '    if obj.name == "Moe Szyslak":\n'
            "        moe = obj\n"
            "        break\n"
            "\n"
            "if moe:\n"
            "    print(\"Moe: 'One Duff, comin' right up.'\")\n"
            '    this.announce(f"Moe slides a Duff beer down the bar to {context.player.name}.")\n'
            "    system = lookup(1)\n"
            '    beer = create("Duff beer", parents=[system.thing], location=context.player)\n'
            '    beer.set_property("description", "Cold can of Duff beer, Springfield\'s favorite beverage.")\n'
            '    print("*A cold Duff beer appears in your inventory*")\n'
            "else:\n"
            '    print("There\'s nobody behind the bar right now.")\n'
        ),
    },
]


# ---------------------------------------------------------------------------
# Phase 9: Test verb
# ---------------------------------------------------------------------------
TEST_VERB = {
    "verb": "test-moes-tavern",
    "obj": "$programmer",
    "code": (
        "from moo.sdk import lookup, NoSuchObjectError, NoSuchVerbError\n"
        "\n"
        "passed = 0\n"
        "failed = 0\n"
        "\n"
        "def ok(label):\n"
        "    global passed\n"
        "    passed += 1\n"
        '    print(f"[green]PASS[/green] {label}")\n'
        "\n"
        'def fail(label, reason=""):\n'
        "    global failed\n"
        "    failed += 1\n"
        '    suffix = f": {reason}" if reason else ""\n'
        '    print(f"[red]FAIL[/red] {label}{suffix}")\n'
        "\n"
        'print("[bold]--- Rooms ---[/bold]")\n'
        "rooms = {}\n"
        "for name in [\n"
        '    "Moe\'s Tavern - Main Bar",\n'
        "    \"Moe's Tavern - Men's Room\",\n"
        '    "Moe\'s Tavern - Ladies Room",\n'
        '    "Moe\'s Tavern - Back Room",\n'
        '    "Moe\'s Tavern - Secret Room",\n'
        "]:\n"
        "    try:\n"
        "        rooms[name] = lookup(name)\n"
        "        ok(name)\n"
        "    except NoSuchObjectError as e:\n"
        "        rooms[name] = None\n"
        "        fail(name, str(e))\n"
        "\n"
        'print("[bold]--- Objects in Main Bar ---[/bold]")\n'
        'mb = rooms.get("Moe\'s Tavern - Main Bar")\n'
        "if mb:\n"
        "    names = [o.name for o in mb.contents.all()]\n"
        '    for t in ["bar counter", "bar stool", "pool table", "pool cue",\n'
        '               "jukebox", "wall phone", "TV", "love tester", "peanuts",\n'
        '               "Duff beer", "Moe Szyslak", "Barney Gumble", "Homer Simpson"]:\n'
        "        if any(t.lower() in n.lower() for n in names):\n"
        '            ok(f"Main Bar: {t}")\n'
        "        else:\n"
        '            fail(f"Main Bar: {t}", f"not in {names}")\n'
        "\n"
        'print("[bold]--- Objects in Men\'s Room ---[/bold]")\n'
        "mr = rooms.get(\"Moe's Tavern - Men's Room\")\n"
        "if mr:\n"
        "    names = [o.name for o in mr.contents.all()]\n"
        '    for t in ["toilet", "sink", "mirror", "broken lock"]:\n'
        "        if any(t.lower() in n.lower() for n in names):\n"
        '            ok(f"Men\'s Room: {t}")\n'
        "        else:\n"
        '            fail(f"Men\'s Room: {t}", f"not in {names}")\n'
        "\n"
        'print("[bold]--- Objects in Ladies Room ---[/bold]")\n'
        'lr = rooms.get("Moe\'s Tavern - Ladies Room")\n'
        "if lr:\n"
        "    names = [o.name for o in lr.contents.all()]\n"
        '    for t in ["toilet", "desk", "boxing poster", "tampon dispenser"]:\n'
        "        if any(t.lower() in n.lower() for n in names):\n"
        '            ok(f"Ladies Room: {t}")\n'
        "        else:\n"
        '            fail(f"Ladies Room: {t}", f"not in {names}")\n'
        "\n"
        'print("[bold]--- Objects in Back Room ---[/bold]")\n'
        'br = rooms.get("Moe\'s Tavern - Back Room")\n'
        "if br:\n"
        "    names = [o.name for o in br.contents.all()]\n"
        '    for t in ["beer keg", "supply boxes", "shotgun", "shady door"]:\n'
        "        if any(t.lower() in n.lower() for n in names):\n"
        '            ok(f"Back Room: {t}")\n'
        "        else:\n"
        '            fail(f"Back Room: {t}", f"not in {names}")\n'
        "\n"
        'print("[bold]--- Verbs ---[/bold]")\n'
        "verb_checks = [\n"
        '    ("wall phone", "call"),\n'
        '    ("Duff beer", "drink"),\n'
        '    ("pool table", "play"),\n'
        '    ("jukebox", "play"),\n'
        '    ("love tester", "test"),\n'
        '    ("tampon dispenser", "use"),\n'
        '    ("Moe Szyslak", "order"),\n'
        '    ("Barney Gumble", "talk"),\n'
        '    ("Homer Simpson", "talk"),\n'
        "]\n"
        "for obj_name, verb_name in verb_checks:\n"
        "    try:\n"
        "        obj = lookup(obj_name)\n"
        "        obj.get_verb(verb_name)\n"
        '        ok(f"{obj_name}: {verb_name}")\n'
        "    except NoSuchObjectError as e:\n"
        '        fail(f"{obj_name}: {verb_name}", f"object not found: {e}")\n'
        "    except NoSuchVerbError:\n"
        '        fail(f"{obj_name}: {verb_name}", "verb not found")\n'
        "\n"
        'print(f"[bold]{passed}/{passed+failed} checks passed.[/bold]")\n'
    ),
}


def main():
    print("=== Moe's Tavern Build Script ===", file=sys.stderr)
    print("Connecting to local DjangoMOO...", file=sys.stderr)

    with MooSSH() as moo:
        moo.run("look")

        print("\n--- Reloading @edit verb ---", file=sys.stderr)
        moo.run("@reload @edit on $programmer")

        print("\n--- Phase 1: Rooms and exits ---", file=sys.stderr)
        for cmd in ROOMS:
            moo.run(cmd)

        print("\n--- Phase 2: Main Bar objects ---", file=sys.stderr)
        duff_ref = build_main_bar_objects(moo)

        print("\n--- Phase 3: Men's Room objects ---", file=sys.stderr)
        build_mens_room_objects(moo)

        print("\n--- Phase 4: Ladies Room objects ---", file=sys.stderr)
        build_ladies_room_objects(moo)

        print("\n--- Phase 5: Back Room objects ---", file=sys.stderr)
        build_back_room_objects(moo)

        print("\n--- Phase 6: Secret Room objects ---", file=sys.stderr)
        build_secret_room_objects(moo)

        print("\n--- Phase 7: NPCs ---", file=sys.stderr)
        build_npcs(moo)

        # Map names that have duplicates to their captured #N ref
        obj_refs = {"Duff beer": duff_ref}

        print("\n--- Phase 8: Interactive verbs ---", file=sys.stderr)
        for spec in VERBS:
            obj_ref = obj_refs.get(spec["obj"], spec["obj"])
            set_verb(moo, spec["verb"], obj_ref, spec["code"])

        print("\n--- Phase 9: Test verb ---", file=sys.stderr)
        set_verb(moo, TEST_VERB["verb"], TEST_VERB["obj"], TEST_VERB["code"])

        print("\n--- Running @test-moes-tavern ---", file=sys.stderr)
        moo.run("@test-moes-tavern")

    print("\n=== Build complete. ===", file=sys.stderr)
    print("SSH in and run '@test-moes-tavern' to verify.", file=sys.stderr)


if __name__ == "__main__":
    main()
