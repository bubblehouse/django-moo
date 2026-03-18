---
name: game-designer
description: Design and build themed multi-room environments in DjangoMOO via SSH wizard commands. Triggered by: "build a MOO environment", "create rooms for X", "design a location based on Y", "add NPCs for Z", "write a test verb for", "set up a MOO area", "implement a themed space in MOO".
compatibility: DjangoMOO project (django-moo). Requires a wizard SSH session.
---

# Game Designer Skill

You are designing and building a themed multi-room environment in DjangoMOO. Follow this 5-phase workflow.

## Phase 1: Research

Before writing any commands, research the theme thoroughly:

- Physical layout: How many rooms? What are their names and spatial relationships?
- Objects: What items are present? Which are interactive vs. decorative?
- Characters: Who lives here? What do they say or do?
- Signature interactions: What verbs make this space feel alive? (sit, drink, order, throw, play)
- Atmosphere: What descriptions capture the feel of each room?

Use web research for real-world locations. Aim for specificity — generic descriptions produce generic spaces.

## Phase 2: Design

Produce a design document before writing any commands:

1. **Room list** with names and one-sentence descriptions
2. **Exit map** showing which rooms connect and in which directions
3. **Parent classes** — if 4+ objects share behavior, define a Generic parent class first
4. **Object instances** per room, with parent class and key properties
5. **NPC roster** with names, parent class, and sample dialogue lines
6. **Verb list** — which verbs go on which objects/classes, and what they do
7. **Test checklist** — enumerate every room, exit pair, object, and verb to be verified

## Phase 3: Prerequisites

Before issuing build commands, confirm:

- `@edit` supports verb/property creation syntax (`@edit verb <name> on "<obj>"`) — requires updated `at_edit.py`
- `@test-<name>` verb will be placed on `$programmer` so any programmer can run it
- Parent class names are finalized and won't conflict with existing objects

## Phase 4: Build Sequence

Issue commands in this order. See `references/moo-commands.md` for exact syntax.

1. Create parent classes (`@create "Generic X" from "$thing"` or `"$player"` for NPCs)
2. Add verbs to parent classes (`@edit verb <name> on "Generic X"`)
3. Add properties to parent classes (`@edit property <name> on "Generic X" with <value>`)
4. Create the first room if needed (you start somewhere — `@dig` from there)
5. `@dig` each room, noting the exit object name created
6. `@tunnel` reverse exits
7. `@describe` each room
8. Create object instances (`@create "<name>" from "<parent>"`)
9. `@describe` each object
10. `@move` objects to their rooms
11. Set instance-specific properties (`@edit property <name> on "<obj>" with <value>`)
12. Create NPC instances, `@move` to rooms, `@gender`, set `lines` property
13. `@lock` any exits that need conditions
14. Write the `@test-<name>` verb (Phase 5)

## Phase 5: Test Verb

Write the full `@test-<name>` verb using the template in `assets/test-verb-template.md`.

Place it on `$programmer` with: `@edit verb test-<name> on "$programmer"`

The verb must cover:
- Every room (lookup by name)
- Every exit pair (direction + destination)
- Every named object in each room
- Every NPC
- Key verbs on parent classes

See `assets/test-verb-template.md` for the full code structure.

## Reference Files

- `references/moo-commands.md` — exact syntax for all build commands
- `references/verb-patterns.md` — RestrictedPython code patterns for interactive verbs
- `references/object-model.md` — parent classes, properties, exits, NPCs
- `assets/test-verb-template.md` — `@test-<name>` verb template
