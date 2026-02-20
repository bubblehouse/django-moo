# Bootstrapping

While the contents of this guide cover the essential elements of any DjangoMOO environment, to
actually do anything interesting you need to boostrap your database with some essential objects.

Right now there are two datasets defined, `test` and `default`. The `test` dataset is used in the
core unit tests. It contains verbs and properties that have no real value outside of the tests.

`default` is a lot more interesting, and is the dataset used when you initialize a new DjangoMOO
database with:

    docker compose run webapp manage.py moo_init

## Initialization

Every new environment needs a few things to be at all useable:

* Object #1 is created as the "System Object"
  * Must define a verb `set_default_permissions` that gets run for every new object
* Must have an object named "container class" that defines the `enter` verb
* Must have an object named "Wizard" that is the admin account for the dataset
* All these objects should be owned by Wizard

These steps are handled by `moo.core.bootstrap.initialize_dataset()`:

```{eval-rst}
.. py:currentmodule:: moo.core.bootstrap
.. autofunction:: initialize_dataset
```

Once all the objects are created and necessary properties created, the `moo.core.bootstrap.load_verbs()` function can load all the verb code

```{eval-rst}
.. autofunction:: load_verbs
```

## Bootstrap File Organization

The bootstrap system is organized into several files:

- **`default.py`**: Creates the production game world with rooms, players, and other game objects
- **`test.py`**: Creates a minimal test dataset used by pytest
- **`default_verbs/`**: Directory containing verb files for the default dataset
- **`test_verbs/`**: Directory containing verb files for the test dataset

## Verb Files in Bootstrap

Bootstrap verb files follow a specific format with a shebang line that defines metadata:

```python
#!moo verb verb_name --on $object_reference
```

The shebang line specifies:
- Verb name(s) - the name(s) by which the verb can be invoked
- `--on` - the object to attach the verb to (uses `$property` syntax to reference system object properties)
- Optional flags like `--dspec` and `--ispec` for direct/indirect object specifiers

After the shebang line, the verb code follows (without a function wrapper - RestrictedPython adds that).

### Example Bootstrap Verb

```python
#!moo verb accept --on $room

"""Accept an object being moved into this verb's location."""
# Verb code here
return True
```

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
from moo.core import bootstrap, create, lookup, code

repo = bootstrap.initialize_dataset("my_game")
wizard = lookup("Wizard")

# Create custom game objects
library = create("Grand Library", location=None)
library.set_property("description", "A vast library filled with books.", inherited=True)

# Add a verb
library.add_verb("browse", code="""
return "You browse the shelves..."
""")
```

## Bootstrap Best Practices

1. **Use `lookup()` to find objects**: Don't hardcode object IDs, use `lookup("object_name")` to find them
2. **Set inherited=True for properties**: Child objects should inherit parent properties by default
3. **Grant appropriate permissions**: Use `allow()` to set permissions for wizards, owners, and everyone
4. **Document the object hierarchy**: Include comments about which objects should be parents of others
5. **Test bootstrap data**: Create tests that verify the bootstrap dataset loads correctly
6. **Keep bootstrap files focused**: Separate default game data from test data

## Running Bootstrap in Development

```bash
# Initialize the database with bootstrap data
python manage.py moo_init

# Reset the database (caution: deletes everything!)
python manage.py migrate zero
python manage.py migrate
python manage.py moo_init

# Test bootstrap in Django shell
python manage.py shell
>>> from moo.core import lookup
>>> root = lookup("root")
>>> root.name
'Root Class'
```
