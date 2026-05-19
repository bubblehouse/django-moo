+++
date = '2026-05-19T00:00:00-04:00'
draft = false
title = 'Translating Zork 1 to DjangoMOO'
+++

There's a working Zork 1 running on DjangoMOO now. The translator and the generated bootstrap live in [moo-agent](https://gitlab.com/bubblehouse/moo-agent) — the experimental sibling repo that holds the AI integration work and other side projects — and load into a stock DjangoMOO instance in place of the default world. The engine itself didn't get a Zork mode: same RestrictedPython sandbox, same parser, same object model as 1.x, with the Zork content sitting on top as data and verb source.

The smoke harness currently passes about 330 of Zork's 350 score points on the canonical walkthrough. Getting there was mostly translator work plus a long shakedown loop — play through, log every divergence from canonical Zork, fix the importer, replay. The rest of this post is about that loop.

## Why Zork

DjangoMOO is a niche project. Recruiting contributors to play and stress-test the default world is hard, and the default bootstrap is small enough that organic play barely exercises the engine. A pre-existing game with a canonical walkthrough and forty years of player testing baked in is the closest thing to free QA the project has access to.

Zork is also a good adversarial target. ZIL is dense, declarative, full of Z-machine primitives — `FSET`/`FCLEAR`, `GETP`/`PUTP`, tables, queue-based daemons — and parser conventions that didn't grow up around the LambdaMOO object model. Mapping all of that onto Django objects plus Python verbs forced real decisions about how generic the engine actually had to be.

Translating instead of hand-porting was the only honest version of the test. If the engine could host translator output verbatim, the engine was actually general. Anywhere the translation got blocked, either the translator needed to do more work or the engine needed a real, game-neutral capability it didn't have yet.

## The pipeline

The importer lives at [`extras/zil_import/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/extras/zil_import) in the moo-agent repository. Three stages:

| Stage | Files | Job |
|---|---|---|
| **Parse** | [`parser.py`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/zil_import/parser.py), [`ir.py`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/zil_import/ir.py), [`converter.py`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/zil_import/converter.py) | Read `.zil` source into IR dataclasses with flag and property mappings. |
| **Translate** | [`translator/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/extras/zil_import/translator) | Walk the IR and emit per-routine, per-clause Python verb sources. `COND`/`AND`/`OR` chains, M-clause action dispatchers, and bare-T trailing-value idioms each get their own handler. |
| **Generate** | [`generator/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/extras/zil_import/generator) | Drive translator output into a complete bootstrap tree — rooms, objects, exits, tables, daemons — organised by verb owner: [`verbs/zork_thing/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/moo/bootstrap/zork1/verbs/zork_thing), [`verbs/zork_actor/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/moo/bootstrap/zork1/verbs/zork_actor), and per-room directories under [`verbs/rooms/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/moo/bootstrap/zork1/verbs/rooms). |

The translator emits calls into a runtime shim layer (flag predicates, zstate accessors, table walkers, queue and scheduler primitives) rather than into engine internals. The intent is that the shim shrinks over time as translator quality improves — fewer runtime helpers, more direct emission of idiomatic Python.

The whole generated tree is checked in at [`moo/bootstrap/zork1/`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/moo/bootstrap/zork1). Regeneration isn't part of normal CI; the output is treated as a build artifact you commit.

## The boundary

The working rule on this project is that the engine doesn't learn about Zork. Translation gaps get solved inside the importer, not inside [`moo/core/`](https://gitlab.com/bubblehouse/django-moo/-/tree/main/moo/core), [`moo/sdk/`](https://gitlab.com/bubblehouse/django-moo/-/tree/main/moo/sdk), or the shared [`moo/bootstrap/`](https://gitlab.com/bubblehouse/django-moo/-/tree/main/moo/bootstrap) loader.

The rule isn't absolute. A handful of engine improvements did land during this work — parser conveniences, lifecycle hooks, a couple of property-lookup optimisations — but only when the underlying need was genuinely general. The filter was: would this still make sense if Zork didn't exist? Anything Zork-specific stays in the importer.

The cost is real. There were several points where a one-line patch in the engine would have fixed a translation bug; the rule forced a more general translator-side or shim-side fix instead. The payoff is that the 1.x engine is the engine that hosts Zork. No `--zork` flags, no special-case classes, no Z-machine primitives leaking into core code. A regression test grep-scans for primitive leakage and fails if any appears outside the shim layer.

## Shakedown

The bug-finding workflow was deliberately simple: open one long-lived SSH session, drive the canonical walkthrough, log every divergence to a `BUGS.md` ledger with a hypothesis and workaround, then keep playing. Don't stop to fix anything mid-session. Fixes happen separately, in a different mode, after a round of shakedown produces a queue of entries to attack.

The bugs were almost never what you'd guess from a clean reading of the source.

* `look in <closed container>` returned "The X is empty." for both closed and empty cases, because the substrate's `examine` verb delegated the entire branch to `V-LOOK-INSIDE` and never reached the descriptive line. The fix was a substrate verb override that prints the description first, then conditionally adds the contents view.

* `drink water` printed the internal placeholder name `LOCAL-GLOBALS` because the scenery filter was comparing uppercase ZIL atom strings (`"GLOBAL-WATER"`) against snake-case alias rows (`["water", "global_water", ...]`). The `IN` filter never matched, the global-water resolution always returned False, and the drinkable branch fell through to an error message using the placeholder object's name. One-line normalisation in [`global_in`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/zil_import/verbs/zork_root/output.py).

* The `i_thief` daemon — the wandering NPC who pickpockets the player — was timing out the 15-second Celery hard limit. Each tick walked roughly 110 rooms and called `.flag()` twice per room, around 220 verb dispatches per second. Caching the static "outdoor non-sacred" room PK list on the System Object on first use brought cold ticks to about 77ms and warm ticks to 27ms.

* `take <obj>` after the thief stole and re-dropped an item would report "Taken." but show nothing in inventory. The canonical `STEAL-JUNK` routine sets `invisible=True` on bagged items; the take substrate wasn't clearing the flag when the object came back into the player's hands. Three lines in the substrate verb fixed it.

The pattern across rounds is consistent. ZIL idioms that depend on something the translator approximated reveal themselves only under actual play. The walkthrough surfaces them; the importer absorbs them.

## Where AI fit

The earlier post on this site described skill files and persistent memory. The Zork work is the largest sustained use of that machinery so far.

[`zork-shakedown`](https://gitlab.com/bubblehouse/moo-agent/-/tree/main/extras/skills/zork-shakedown) is a Claude Code skill: a long-lived SSH session harness built on [`MooSSH`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/skills/game-designer/tools/moo_ssh.py) (a small Python client that brackets each command's output with PREFIX/SUFFIX markers so the harness can tell where a response begins and ends), a coverage checklist, the [`BUGS.md`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/skills/zork-shakedown/BUGS.md) ledger, a [`completed-work.md`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/skills/zork-shakedown/references/completed-work.md) log, and [`rule-zero.md`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/skills/zork-shakedown/references/rule-zero.md) — the do-not-touch-the-engine constraint with a list of anti-patterns that already got attempted and reverted. Every session updates these files with whatever it learned that session: a new failure mode, a new fix that landed, a pre-existing limitation that surfaced.

The loop in practice: an AI session opens the harness, drives canonical commands, logs divergences to `BUGS.md`. In fix mode it picks an entry, traces the cause, lands a change in `extras/zil_import/`, regenerates the bootstrap, syncs it into the running container, and re-runs the smoke harness. Score is recorded. Anything learned about the engine's limits goes back into the skill files for the next session.

Persistent memory carries the most weight on rule-zero discipline. Without it, every new session would relearn the same lesson — a moo-core patch fixes the bug fastest, and the engine slowly accretes Zork-shaped scar tissue. With it, the constraint is the first thing every session loads, and the temptation to fix-forward into core code gets caught early.

The remaining gap is mostly a couple of canonical pickpocket cascades (the thief stealing the crystal skull from Land of the Dead is in his actual walk cycle — that one's not a bug) plus a handful of edge-case puzzle gates still queued in `BUGS.md`.

## What it bought

The real payoff isn't that Zork runs on DjangoMOO. It's that Zork exercises the engine far more thoroughly than the default bootstrap could realistically manage for the foreseeable future. The default world has rooms, mail, containers, and lighting. Zork has a wandering NPC who pickpockets the player, a maze, a vehicle with terrain rules, multi-stage puzzle gates, a clock-driven daemon scheduler, and decades of player-attested edge cases. Every shakedown round that closes a Zork bug also raises the floor for everything else the engine will ever host.

The importer itself stays game-agnostic. Anyone with a ZIL game can drop a [`game_config.py`](https://gitlab.com/bubblehouse/moo-agent/-/blob/main/extras/zil_import/game_config.py) for their banner and atom map; the translator and generator are unchanged.

If you want to try it locally: clone [django-moo](https://gitlab.com/bubblehouse/django-moo), install the [moo-agent](https://gitlab.com/bubblehouse/moo-agent) package (which ships the `zork1` bootstrap), `docker compose up`, and run `moo_init --bootstrap zork1`. Connect over SSH to the running container and pick up the leaflet.
