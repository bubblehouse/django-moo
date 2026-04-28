# Bootstrap Recipes

Practical recipes for working with bootstrap datasets. For the package
layout and a full walkthrough of building a new dataset from scratch,
see {doc}`../tutorials/custom-world`. For function reference (signatures
and arguments), see {doc}`../reference/bootstrapping`.

## Sync verbs after editing source files

When you've edited a `.py` file under `<dataset>_verbs/` and want the
running database to pick up the change without resetting:

```bash
docker compose run webapp manage.py moo_init --bootstrap default --sync
```

`--sync` re-runs the bootstrap orchestrator against the existing
database. `get_or_create_object` skips objects that already exist;
`bootstrap.load_verbs(repo, ..., replace=True)` overwrites verb source
in place.

If you've made structural changes (new objects, changed parents) the
script that creates them will pick up the difference on the next
`--sync` because `get_or_create_object` is idempotent.

## Add a verb to an existing dataset

Drop a new `.py` file under `<dataset>_verbs/<class>/` with a shebang
and the verb body:

```python
#!moo verb peek --on $thing --dspec this
print(f"You peek at {this.name}.")
```

Then sync:

```bash
docker compose run webapp manage.py moo_init --bootstrap default --sync
```

`load_verbs` walks the verb package recursively, so the location of
the file inside the package doesn't matter for dispatch — only the
`--on` line in the shebang determines where the verb attaches. The
`<class>/` subdirectory is a convention for human readers.

## Update an existing verb in place

Edit the source file. The next `--sync` overwrites the existing `Verb`
row because `load_verbs` is called with `replace=True` during sync.
There's no need to delete the old verb first.

If the new shebang changes the verb's `--on` target, the old `Verb` row
stays attached to the old object and a fresh `Verb` row is created on
the new object. To clean up the orphan, delete it manually via the
admin or with a one-shot finalize script (see
`moo/bootstrap/default/999_finalize.py` for an example).

## Test a custom bootstrap

Use the `t_init` fixture from `moo/conftest.py` to bootstrap any in-tree
dataset before a test runs:

```python
import pytest
from moo.core import code, parse
from moo.sdk import lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["mygame"], indirect=True)
def test_starting_room_loads(t_init: Object, t_wizard: Object):
    start = lookup("Starting Square")
    assert start is not None
```

Place tests under `<dataset>_verbs/tests/` (e.g.
`moo/bootstrap/mygame_verbs/tests/test_world.py`).

Run with:

```bash
uv run pytest -n auto moo/bootstrap/mygame_verbs/tests/
```

## Make a property inherit ownership

By default, when a child object inherits a property from its parent,
the child's owner becomes the property's owner on the child. Pass
`inherit_owner=True` when setting the property to keep the parent's
owner on every child:

```python
player.set_property("ps", "they", inherit_owner=True)
```

Use this when a wizard-owned verb on the parent class needs to set the
property on a child whose owner is a different player. Without
`inherit_owner=True`, the verb would lose write access to that property
on every player who isn't a wizard. See
`moo/bootstrap/default/010_core_classes.py` for many examples.

## Allow non-wizards to create instances of a class

By default, only the owner and wizards can create children of an
object. To let any player run `@create "name" from $myclass`, grant the
`derive` permission to `everyone`:

```python
from moo.core.models.acl import Access, Permission

derive_perm = Permission.objects.get(name="derive")
Access.objects.get_or_create(
    object=my_class,
    permission=derive_perm,
    type="group",
    group="everyone",
    rule="allow",
)
```

`get_or_create` makes the grant idempotent. `moo/bootstrap/default/999_finalize.py`
applies this to every standard system class (`root`, `thing`, `room`,
`exit`, `player`, etc.) in a single loop.

## Update an object's properties idempotently

`get_or_create_object` returns `(object, created)`. The boolean lets
you separate one-time setup from updates that should run every time:

```python
room, created = bootstrap.get_or_create_object(
    "Starting Square", unique_name=True, parents=[room_class],
)
if created:
    # First-run setup that should never re-fire
    sys.set_property("player_start", room)
# Always re-apply: cheap idempotent updates
room.set_property("description", "A flat stone square...")
```

Calls to `set_property` overwrite cleanly on each run, so they're safe
to put outside the `if created:` block. Operations that aren't
naturally idempotent (e.g. `obj.contents.add(...)` on a M2M with
duplicate semantics) belong inside the gate.

## Replace a verb's `--on` target

If you need to move a verb from one class to another:

1. Edit the verb file's shebang to point at the new class.
2. Move the file into `<dataset>_verbs/<new_class>/`.
3. Run `--sync` to create the verb on the new class.
4. Add a one-shot deletion in your finalize script to remove the orphan
   on the old class:

   ```python
   from moo.core.models import Verb
   Verb.objects.filter(
       origin=old_class,
       filename__endswith="/old_class/myverb.py",
   ).delete()
   ```

5. After every deployed database has run `--sync`, remove the deletion.

`moo/bootstrap/default/999_finalize.py` contains a real example of this
cleanup pattern (the `_moved_from_player` block).

## Debug a failing bootstrap

`moo_init` wraps the orchestrator in a single transaction, so any
exception rolls back everything. To see what went wrong:

```bash
docker compose logs webapp | tail -100
```

Common causes:

- `IntegrityError` on a unique field — a script created an object via
  raw `create()` instead of `get_or_create_object`.
- `NoSuchObjectError` from a `lookup("X")` — the script ran before the
  script that creates `X`. Check the numeric prefixes (`010_`, `020_`,
  ...) and adjust ordering.
- `AttributeError` on an injected name — the `_namespace` dict in
  `__init__.py` doesn't include that name. Add it.
