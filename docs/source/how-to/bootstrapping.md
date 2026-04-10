# How to Create a Custom Bootstrap Dataset

For reference on the bootstrap file format, initialization system, and built-in datasets, see {doc}`../reference/bootstrapping`.

## Creating Your Own Bootstrap Dataset

To create a custom bootstrap dataset:

1. Create a new Python file in the bootstrap directory (e.g., `my_game.py`)
2. Call `initialize_dataset("my_game")` to set up the base system object
3. Create objects using `create()` and `lookup()`
4. Set properties on objects with `set_property()`
5. Add verbs using `add_verb()`
6. Place verb files in a corresponding directory (e.g., `my_game_verbs/`)

### Example Custom Bootstrap

```python
from moo.core import bootstrap, code
from moo.sdk import create, lookup

repo = bootstrap.initialize_dataset("my_game")
wizard = lookup("Wizard")

# Create custom game objects
library = create("Grand Library", location=None)
library.set_property("description", "A vast library filled with books.")

# Add a verb
library.add_verb("browse", code="""
return "You browse the shelves..."
""")
```

## Bootstrap Best Practices

1. Use `lookup()` to find objects: don't hardcode object IDs, use `lookup("object_name")` to find them.
2. When to set `inherit_owner=True` for properties: used to keep inherited properties usable by a verb that runs as the author.
3. Grant appropriate permissions: use `allow()` to set permissions for wizards, owners, and everyone.
4. Document the object hierarchy: include comments about which objects should be parents of others.
5. Test bootstrap data: create tests that verify the bootstrap dataset loads correctly.
6. Keep bootstrap files focused: separate default game data from test data.

## Syncing Verbs After Changes

After modifying verb source files in a built-in dataset, use `moo_init --sync`
to push updates to an existing database without resetting it:

    docker compose run webapp manage.py moo_init --sync

Bootstrap helpers (`get_or_create_object`, `load_verbs`) are idempotent — they
skip objects and verbs that already exist unless `replace=True` is passed.
`load_verbs` called during sync always passes `replace=True`.

Custom bootstrap files must use `get_or_create_object` instead of `create()` for
all top-level objects to benefit from idempotency. Using raw `create()` will raise
`IntegrityError` when sync is run against a database that already contains those
objects.
