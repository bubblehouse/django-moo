# Your First MOO Verb

This tutorial walks you through creating, editing, and testing a MOO verb from scratch. By the end you'll have written working Python code that runs inside the MOO, know how to send output to players, and know how to accept command arguments.

## Prerequisites

Before you start:

- A running DjangoMOO development environment (see {doc}`../how-to/development`)
- An SSH connection to the server as the Wizard user

To connect, run:

```bash
ssh -p 8022 Wizard@localhost
```

You should see a `$` prompt when you're in.

## Step 1: Orient yourself

Type `look` and press Enter. You should see something like:

```
The Void
You are floating in a featureless expanse. There is nothing here.
```

Type `@who` to confirm you're connected as Wizard:

```
Wizard (connected)
```

Good. As Wizard you can create and edit verbs anywhere.

## Step 2: Create and edit a verb

MOO verbs live on objects. The simplest place to put your first verb is on yourself — the Wizard object. Run:

```
@edit verb greet on me
```

This creates a new verb named `greet` on the Wizard object and opens the built-in editor. The status bar at the bottom shows the available keybindings:

```
[Ctrl+S] Save  [Ctrl+C/Q] Cancel
```

Type this as the verb body:

```python
print("Hello, world!")
```

Press `Ctrl+S`, then `Y` to confirm the save. The editor closes and you're back at the prompt.

## Step 3: Test it

Type `greet`:

```
$ greet
Hello, world!
```

You just ran your first MOO verb. `print()` sends output back to you, the caller, buffered until the verb finishes.

## Step 4: Accept an argument

Let's update `greet` to accept a name. Open the editor again:

```
@edit verb greet on me
```

Replace the code with:

```python
#!moo verb greet --on me --dspec any
name = parser.get_dobj_str()
print(f"Hello, {name}!")
```

Save with `Ctrl+S` → `Y`.

The shebang line on the first line registers `--dspec any`, which tells the parser that this verb requires a direct object. When the verb fires, `get_dobj_str()` is guaranteed to return a string — if the player types `greet` with nothing after it, the parser won't dispatch the verb at all.

`--on` is required for the shebang to be parsed at all — without it the line is silently ignored and the dspec update won't apply. When editing interactively, `--on` has no other effect: the verb stays on whatever object the `@edit verb ... on <object>` command attached it to.

Test it:

```
$ greet world
Hello, world!

$ greet
I don't understand that.
```

The second response comes from the parser itself, not your code, because `--dspec any` prevented dispatch.

## What just happened

**`parser`** is always available in verb code. `get_dobj_str()` returns the direct object as a plain string — whatever the player typed after the verb name. It raises `NoSuchObjectError` if nothing was typed, so when `--dspec any` is in place you can call it unconditionally. Only catch the exception if you want to provide a custom message or fallback behavior.

**`print()`** sends a line of text to the player who ran the command. For output to other players in the room, use `context.player.location.announce_all_but(context.player, msg)` instead.

**`return "some message"`** does not display anything. A bare `return` exits the verb early; the string value is silently discarded. Always use `print()` for player-visible output.

**The shebang line** is how verb dispatch properties are set. `--on` names the object the verb lives on (required for the shebang to parse — without it the whole line is silently ignored). When editing interactively, the verb stays wherever `@edit verb ... on <object>` put it; `--on` in the shebang doesn't move it. `--dspec any` means a direct object must be present. `--dspec either` makes it optional. Omitting `--dspec` (or `--dspec none`) means the verb only matches when no direct object is given. See {doc}`../how-to/creating-verbs` for the full shebang syntax including `--ispec` for indirect objects.

## Step 5: Make it permanent (optional)

Verbs created with `@edit verb` live in the database and survive server restarts, but not a full database reset (`moo_init`). If you want this verb to be part of your bootstrap dataset, add a verb file in `default_verbs/`. See {doc}`../reference/bootstrapping` for how that works.

## Where to go next

- {doc}`../how-to/creating-verbs` — Complete guide to verb code format, the full shebang syntax, parser API, error handling, and output mechanisms
- {doc}`../how-to/advanced-verbs` — Calling other verbs, async patterns, time-limited tasks, SDK functions
- {doc}`../reference/runtime` — The `context` variable and all its attributes
- {doc}`../reference/parser` — Full reference for parser methods: `get_pobj_str()`, `has_dobj_str()`, and more
