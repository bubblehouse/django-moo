# Building a Persistent World from Scratch

> **Most readers do not need this tutorial.** A from-scratch world means
> writing your own root class hierarchy, your own `look`/`take`/`drop`/
> `go`/`say` equivalents, and your own connection callbacks. None of the
> helpers in `default_verbs/` apply — every command vocabulary is
> something you define. Expect this to take days, not hours.
>
> If what you actually want is to add rooms, items, or themed areas to
> the existing MOO, extend the `default` dataset by adding numbered
> scripts under `moo/bootstrap/default/`. The reasonable use cases for
> this tutorial are narrow: implementing a different game engine on top
> of the MOO substrate (e.g., a Zork-style adventure interpreter), or a
> non-MOO theme that should not share any state with the standard player
> commands.

This tutorial walks through building a standalone bootstrap dataset as a
Python package. After you're done, somebody can install your package and
run `moo_init --bootstrap mygame` to bring up your world from an empty
database.

## Prerequisites

Before you start:

- Familiarity with {doc}`first-verb` and {doc}`testing-verbs`
- A working development environment (see {doc}`../how-to/development`)
- Comfort reading existing django-moo source. You will want
  `moo/bootstrap/default/` open in another window for reference.

## What you're building

A new top-level package — call it `mygame` — that contains:

- An orchestrator `__init__.py` that initializes the dataset and runs
  numbered sub-scripts in order.
- Numbered sub-scripts that create your root classes, rooms, and other
  objects.
- A sibling `mygame_verbs/` package containing one verb file per
  command, organized by root class.
- A minimal `pyproject.toml` so the package can be installed.

Layout:

```text
mygame/
├── __init__.py            orchestrator
├── 010_classes.py         root classes (your equivalents of Room/Thing/Player)
├── 020_rooms.py           starting rooms
├── 030_exits.py           exits between rooms
└── 999_finalize.py        permission grants and verb loading
mygame_verbs/
├── room/
│   └── look.py
├── thing/
└── player/
pyproject.toml
```

The `mygame_verbs/<class>/` convention mirrors `default_verbs/`. Each
subdirectory holds verbs whose `--on` references that root class.
`bootstrap.load_verbs` walks the tree recursively, so the directory
structure is purely organizational — only the `--on` line in each verb's
shebang determines where the verb is attached.

## A note on packaging

Today, `moo_init` only discovers bootstrap packages that are siblings of
`moo/bootstrap/default/`. There is no `pip install`-and-go path for an
out-of-tree package yet. The practical workflow is:

1. Develop your package in-tree by placing it under
   `moo/bootstrap/mygame/` and `moo/bootstrap/mygame_verbs/`.
2. Add `"mygame"` to the `builtin_templates` list in
   `moo/core/management/commands/moo_init.py`.

The directory structure and code shown below are identical to what an
out-of-tree pip-installable package will eventually need. The closing
section of this tutorial sketches the future shape; for now, the
tutorial itself shows the in-tree variant.

## Step 1: Create the package skeleton

From the django-moo repo root:

```bash
mkdir -p moo/bootstrap/mygame
mkdir -p moo/bootstrap/mygame_verbs/room
mkdir -p moo/bootstrap/mygame_verbs/thing
mkdir -p moo/bootstrap/mygame_verbs/player
mkdir -p moo/bootstrap/mygame_verbs/tests
touch moo/bootstrap/mygame_verbs/__init__.py
```

Each verb subdirectory will hold one `.py` file per verb. You don't need
an `__init__.py` inside the subdirectories — `load_verbs` walks them as
filesystem trees, not as Python packages.

## Step 2: Write the orchestrator

Create `moo/bootstrap/mygame/__init__.py`:

```python
import importlib.resources
import logging

from moo import bootstrap
from moo.core import code, lookup
from moo.core.models import Object

log = logging.getLogger(__name__)
_repo = bootstrap.initialize_dataset("mygame")
wizard = lookup("Wizard")
sys = Object.objects.get(pk=1)

_namespace = {
    "log": log,
    "bootstrap": bootstrap,
    "lookup": lookup,
    "wizard": wizard,
    "sys": sys,
    "repo": _repo,
}

_pkg = importlib.resources.files("moo.bootstrap") / "mygame"
_scripts = sorted(
    (f for f in _pkg.iterdir() if f.name.endswith(".py") and f.name[0].isdigit()),
    key=lambda f: f.name,
)

with code.ContextManager(wizard, log.info):
    for _script in _scripts:
        exec(  # pylint: disable=exec-used
            compile(_script.read_text(encoding="utf8"), _script.name, "exec"),
            _namespace,
        )
```

What this does:

- `bootstrap.initialize_dataset("mygame")` creates the `Repository` row,
  the System Object (`#1`), and the Wizard player. It is idempotent — a
  second call returns the existing repo.
- `_namespace` is the variable scope every numbered sub-script runs
  inside. Anything you put here is available as a bare name to those
  scripts. `lint` will complain about "undefined-variable" inside
  sub-scripts; that's expected, and a `# pylint: disable=undefined-variable`
  comment at the top of each numbered file is conventional.
- `importlib.resources.files(...).iterdir()` finds every numbered `.py`
  file in the package and runs them in sorted name order — so file
  prefixes (`010_`, `020_`) determine load order.
- `code.ContextManager(wizard, log.info)` makes the bootstrap run as the
  Wizard player, so any objects created inherit Wizard ownership. The
  second argument is the writer callback — log lines from `print()` go
  through `log.info`.

This pattern is taken directly from `moo/bootstrap/default/__init__.py`.
Read that file alongside this one — your orchestrator should look very
similar.

## Step 3: Define your root classes

Create `moo/bootstrap/mygame/010_classes.py`:

```python
# pylint: disable=undefined-variable
root, _ = bootstrap.get_or_create_object("MyGame Root", unique_name=True)
sys.set_property("root_class", root)
root.set_property("description", "")

room, _ = bootstrap.get_or_create_object("MyGame Room", unique_name=True, parents=[root])
sys.set_property("room", room)
room.set_property("description", "An empty space.")

thing, _ = bootstrap.get_or_create_object("MyGame Thing", unique_name=True, parents=[root])
sys.set_property("thing", thing)

player, _ = bootstrap.get_or_create_object("MyGame Player", unique_name=True, parents=[root])
sys.set_property("player", player)
```

Two things matter here:

- `bootstrap.get_or_create_object` is the idempotent equivalent of
  `Object.objects.create()`. Calling it twice returns the existing
  object the second time. **Never use `create()` at the top level of a
  bootstrap script** — `moo_init --sync` would raise `IntegrityError` on
  the second run.
- `sys.set_property("room", room)` registers the class on the System
  Object so verbs can reference it as `$room` in their shebang. The same
  goes for `$thing`, `$player`, `$root_class`. Without these
  registrations, `--on $room` won't resolve when `load_verbs` runs.

You are deliberately *not* parenting on `Generic Room` or any other
class from `default`. This is a fresh world.

## Step 4: Create the starting rooms

Create `moo/bootstrap/mygame/020_rooms.py`:

```python
# pylint: disable=undefined-variable
_rooms = {}

start, _ = bootstrap.get_or_create_object(
    "Starting Square",
    unique_name=True,
    parents=[lookup("MyGame Room")],
)
start.set_property("description",
    "A flat stone square at the centre of an empty plain. "
    "Doors of carved wood face you in three directions.")
_rooms["start"] = start
sys.set_property("player_start", start)

north_hall, _ = bootstrap.get_or_create_object(
    "North Hall",
    unique_name=True,
    parents=[lookup("MyGame Room")],
)
north_hall.set_property("description",
    "A long stone hall lit by sputtering torches.")
_rooms["north_hall"] = north_hall
```

`sys.set_property("player_start", room)` makes that room the spawn point
for new players and the destination of `home` for players without a
custom home.

The `_rooms` dict is local to this script — variables defined in one
sub-script aren't visible to the next. To pass references forward (so
the exit script can reference rooms), stash them on a class or on the
namespace dict. The simplest approach is to look them up by name in the
next script with `lookup("Starting Square")`.

## Step 5: Wire the exits

Create `moo/bootstrap/mygame/030_exits.py`. This step is intentionally
sketchy — every game's exit model is different. The pattern below
mirrors `default`'s, where exits are first-class Objects with a `dest`
property. You may want something simpler.

```python
# pylint: disable=undefined-variable
exit_class, _ = bootstrap.get_or_create_object(
    "MyGame Exit",
    unique_name=True,
    parents=[lookup("MyGame Root")],
)
sys.set_property("exit", exit_class)

start = lookup("Starting Square")
north_hall = lookup("North Hall")

exit_north, _ = bootstrap.get_or_create_object(
    "north",
    parents=[exit_class],
    location=start,
)
exit_north.set_property("dest", north_hall)

exit_south, _ = bootstrap.get_or_create_object(
    "south",
    parents=[exit_class],
    location=north_hall,
)
exit_south.set_property("dest", start)
```

You'll need to write a `go` verb (later) that consults `dest` and moves
the player. None of `default`'s `exit/move.py` applies here — you're
defining the contract yourself.

## Step 6: Add a verb

Create `moo/bootstrap/mygame_verbs/room/look.py`:

```python
#!moo verb look --on $room --dspec none
from moo.sdk import context, NoSuchPropertyError

try:
    desc = this.get_property("description")
except NoSuchPropertyError:
    desc = "There's nothing remarkable to see."

print(this.name)
print(desc)

contents = list(this.contents.exclude(pk=context.player.pk))
if contents:
    names = ", ".join(obj.name for obj in contents)
    print(f"Here: {names}")
```

The shebang says: this is a verb named `look` that lives on whatever
object is registered as `_.room` (your `MyGame Room` class), and it
takes no direct object. Every room you create inherits this verb because
each room is parented on `MyGame Room`.

This is a complete, working `look` verb — but it is *yours*. There is no
inherited `look` from `default`. The same applies to every command you
want players to type: `take`, `drop`, `go`, `say`, `inventory`, and so
on. Each is one file under `mygame_verbs/<class>/`. See {doc}`first-verb`
for the verb-authoring basics.

## Step 7: Finalize and load verbs

Create `moo/bootstrap/mygame/999_finalize.py`:

```python
# pylint: disable=undefined-variable
bootstrap.load_verbs(repo, "moo.bootstrap.mygame_verbs", replace=True)
```

`load_verbs` walks the verb package recursively, parses each shebang,
resolves the `--on` target, and creates or updates the corresponding
`Verb` row. `replace=True` means `moo_init --sync` will overwrite verb
source in place rather than skipping files whose verbs already exist.

Putting `load_verbs` in `999_finalize.py` (rather than directly in
`__init__.py` after the script loop) matches the `default` package's
convention and keeps the orchestrator focused on running scripts.

## Step 8: Register the dataset

Edit `moo/core/management/commands/moo_init.py` and append `"mygame"` to
the `builtin_templates` list near the top of the file:

```python
builtin_templates = ["default", "mygame"]
```

Today this whitelist is the only way to make a custom dataset selectable
via `--bootstrap`. Removing the whitelist in favour of filesystem
discovery is a separate follow-up; until that lands, this manual step is
required.

## Step 9: Run the bootstrap

```bash
docker compose run webapp manage.py migrate
docker compose run webapp manage.py moo_init --bootstrap mygame
```

`moo_init` runs your orchestrator, which runs each numbered script in
order, then loads the verbs. If anything goes wrong it rolls back the
entire transaction — you can fix the bug and re-run.

Once it succeeds:

```bash
docker compose run webapp manage.py createsuperuser --username wizard
docker compose run webapp manage.py moo_enableuser --wizard wizard Wizard
ssh -p 8022 Wizard@localhost
```

Type `look` and you should see your starting room.

## Step 10: Iterate

When you change a verb file, run:

```bash
docker compose run webapp manage.py moo_init --bootstrap mygame --sync
```

`--sync` re-runs your bootstrap against the existing database without
resetting it. `get_or_create_object` skips objects that already exist;
`load_verbs(..., replace=True)` updates verb source in place.

## Step 11: Test it

Tests for your dataset live under `mygame_verbs/tests/`. Use the
`t_init` fixture with your dataset name:

```python
import pytest
from moo.core import code, parse
from moo.sdk import lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["mygame"], indirect=True)
def test_starting_room_has_description(t_init: Object, t_wizard: Object):
    start = lookup("Starting Square")
    assert "stone square" in start.get_property("description")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["mygame"], indirect=True)
def test_look_prints_description(t_init: Object, t_wizard: Object):
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "look")
    assert any("stone square" in line for line in printed)
```

The `t_init` fixture in `moo/conftest.py` accepts any in-tree bootstrap
name; passing `["mygame"]` causes it to bootstrap your dataset before
the test runs.

Run the suite with:

```bash
uv run pytest -n auto moo/bootstrap/mygame_verbs/tests/
```

## Where to look for more

- `moo/bootstrap/default/` — the canonical real-world bootstrap package.
  Read `__init__.py` for the orchestrator pattern, `000_initialize.py`
  through `999_finalize.py` for concrete examples of class definition,
  room creation, player setup, and finalization.
- `moo/bootstrap/default_verbs/<class>/` — verb files organised by
  root-class name. Even though your world doesn't reuse the verbs, the
  directory layout, shebang conventions, and SDK usage are all worth
  copying.
- {doc}`../reference/bootstrapping` — function reference for
  `initialize_dataset`, `get_or_create_object`, `load_verbs`,
  `load_verb_source`, and `parse_shebang`.
- {doc}`../how-to/bootstrapping` — additional bootstrap patterns:
  property inheritance flags, ACL setup, multi-file organisation.

## Out-of-tree packaging (future direction)

The pattern shown above keeps your bootstrap inside django-moo's tree
because that's what `moo_init` supports today. The package shape —
orchestrator, numbered scripts, sibling verb directory — is identical to
what a pip-installable out-of-tree package would need. When entry-point
discovery lands, the change will be straightforward:

- Move `mygame/` and `mygame_verbs/` out of `moo/bootstrap/` into their
  own repository.
- Add an entry-point row to your `pyproject.toml` along the lines of
  `[project.entry-points."moo.bootstrap"]` declaring the bootstrap
  package.
- `moo_init --bootstrap mygame` then resolves the package via
  `importlib.metadata.entry_points` instead of the in-tree filesystem
  scan, and the whitelist in `moo_init.py` goes away.

Until that infrastructure ships, the in-tree path described in this
tutorial is the supported route.
