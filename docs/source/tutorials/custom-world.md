# Building a Persistent World from Scratch

This tutorial walks you through creating a custom bootstrap dataset — a Python file that defines your game world's objects, rooms, and verbs and can be loaded into a fresh database with a single command. By the end you'll have a working tavern with a barrel container, a bartender NPC, and a custom verb, all loaded from code.

## Prerequisites

Before you start:

- A working development environment (see {doc}`../how-to/development`)
- Familiarity with Django management commands (`manage.py`)
- The first-verb tutorial ({doc}`first-verb`) — so you understand the shebang syntax

## What a bootstrap file is

A bootstrap file is a plain Python script that runs inside the Django environment. When `manage.py moo_init` runs it, the script creates objects in the database using the `moo.bootstrap` and `moo.sdk` helpers. Every built-in dataset (`default`, `minimal`) is a bootstrap file — yours will be a peer to those.

## Step 1: Create the bootstrap file

Create `moo/bootstrap/my_game.py`:

```python
import logging
from moo import bootstrap
from moo.core import code
from moo.core.lookup import lookup

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset("my_game")
wizard = lookup("Wizard")

with code.ContextManager(wizard, log.info):
    sys = lookup(1)
```

`initialize_dataset("my_game")` creates the System Object, Wizard user, and required sentinel objects. It is idempotent — safe to run twice. `code.ContextManager(wizard, log.info)` establishes the `wizard` player as the current context for all subsequent operations, so ownership defaults to Wizard.

## Step 2: Create the base classes

Before you can make rooms and things, you need to register the system properties that point to the parent classes:

```python
    from moo.core.models import Object

    root, _ = bootstrap.get_or_create_object("Root Class", unique_name=True)
    root.add_verb("accept", code="return True")
    sys.set_property("root_class", root)

    rooms, _ = bootstrap.get_or_create_object("Generic Room", unique_name=True, parents=[root])
    sys.set_property("room", rooms)

    things, _ = bootstrap.get_or_create_object("Generic Thing", unique_name=True, parents=[root])
    sys.set_property("thing", things)

    player, _ = bootstrap.get_or_create_object("Generic Player", unique_name=True, parents=[root])
    sys.set_property("player", player)
```

`get_or_create_object` returns a `(object, created)` tuple. On subsequent runs it finds the existing object and returns `created=False`, so the `add_verb` and `set_property` calls on `root` and `rooms` are safe to call idempotently too (they update in place).

**Do not use raw `create()` at the top level of a bootstrap file.** `create()` always inserts a new row and will raise `IntegrityError` on a second run. Use `get_or_create_object` for every top-level object.

## Step 3: Create the starting room

```python
    tavern, tavern_created = bootstrap.get_or_create_object(
        "The Rusty Flagon",
        unique_name=True,
        parents=[rooms],
    )
    if tavern_created:
        tavern.set_property("description",
            "A low-ceilinged tavern filled with the smell of sawdust and stale ale. "
            "Scarred wooden tables line the walls.")
    sys.set_property("player_start", tavern.pk)
```

`sys.set_property("player_start", tavern.pk)` makes this room the spawn point for new players (and the destination of `home` for players who have not set a custom home).

## Step 4: Add a container

```python
    containers, _ = bootstrap.get_or_create_object("Generic Container", unique_name=True)
    containers.add_verb("accept", code="return True")
    sys.set_property("container", containers)

    barrel, _ = bootstrap.get_or_create_object(
        "oak barrel",
        unique_name=True,
        parents=[containers],
        location=tavern,
    )
    if barrel.get_property("description", default=None) is None:
        barrel.set_property("description", "A broad oak barrel. The lid is sealed with wax.")
```

## Step 5: Create a verb file

Create the directory `moo/bootstrap/my_game_verbs/thing/` and the file `moo/bootstrap/my_game_verbs/thing/inspect.py`:

```python
#!moo verb inspect --on $thing --dspec this
from moo.sdk import context
print(f"You inspect {this.name} closely.")
context.player.location.announce_all_but(
    context.player,
    f"{context.player.name} inspects {this.name}."
)
```

The shebang registers this verb on `$thing` (the `Generic Thing` class). `--dspec this` means the verb only fires when the direct object resolves to the object the verb is on — so `inspect barrel` dispatches to the barrel's `inspect` verb.

## Step 6: Load verbs from the directory

Back in `my_game.py`, add after the barrel creation:

```python
    bootstrap.load_verbs(repo, "moo/bootstrap/my_game_verbs")
```

`load_verbs` scans the directory recursively for `.py` files with shebang lines, parses the shebang to find the target object and dispatch parameters, and calls `add_verb`. The `repo` argument links each verb to your dataset's repository record so `@reload` can find it.

## Step 7: Register your dataset and run it

Open `moo/core/management/commands/moo_init.py` and add `"my_game"` to `builtin_templates`:

```python
builtin_templates = ["minimal", "default", "my_game"]
```

Now run the bootstrap:

```bash
docker compose run webapp manage.py moo_init --bootstrap my_game
```

Connect and verify:

```bash
ssh -p 8022 Wizard@localhost
```

```
The Rusty Flagon(#N)
A low-ceilinged tavern filled with the smell of sawdust and stale ale...

Contents: oak barrel
Obvious exits: none
```

Try the verb:

```
$ inspect barrel
You inspect oak barrel closely.
```

## Step 8: Iterate with `--sync`

When you edit a verb file, you don't need to reset the database. Run:

```bash
docker compose run webapp manage.py moo_init --bootstrap my_game --sync
```

`--sync` re-runs the bootstrap file against the existing database. `get_or_create_object` skips objects that already exist. `load_verbs` internally passes `replace=True`, so existing verbs are overwritten with the updated source.

## What just happened

`moo_init` wraps your bootstrap file in a database transaction and calls `load_python()` to execute it. `initialize_dataset` ensures the System Object and Wizard exist. `get_or_create_object` is the idempotent equivalent of `create()` — it runs `Object.objects.get_or_create()` under the hood. `load_verbs` walks the verb directory, parses each shebang, looks up the `--on` object via the system property, and calls `add_verb(replace=True)` so sync pushes updates without needing a DB reset.

## Where to go next

- {doc}`../reference/bootstrapping` — Full function reference: `initialize_dataset`, `get_or_create_object`, `load_verbs`, `load_verb_source`, and `parse_shebang`
- {doc}`../how-to/bootstrapping` — Advanced patterns: property inheritance flags, ACL setup, multi-file organisation
- {doc}`testing-verbs` — Write pytest tests for your bootstrap verbs
- {doc}`../reference/permissions` — Set up `allow()` and `@lock` so players can only access certain rooms
