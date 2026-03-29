# Bootstrapping Reference

While the contents of this guide cover the essential elements of any DjangoMOO environment, to
actually do anything interesting you need to bootstrap your database with some essential objects.

Right now there are two datasets defined, `test` and `default`. The `test` dataset is used in the
core unit tests. It uses no additional verb files — only the base objects created by `initialize_dataset()`.

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

These steps are handled by `moo.bootstrap.initialize_dataset()`:

```{eval-rst}
.. py:currentmodule:: moo.bootstrap
.. autofunction:: initialize_dataset
   :no-index:
```

Once all the objects are created and necessary properties created, the `moo.bootstrap.load_verbs()` function can load all the verb code

```{eval-rst}
.. autofunction:: load_verbs
   :no-index:
```

## Bootstrap File Organization

The bootstrap system is organized into several files:

* `default.py`: Creates the production game world with rooms, players, and other game objects
* `test.py`: Creates a minimal test dataset used by pytest; uses no additional verb files
* `default_verbs/`: Directory containing verb files for the `default` dataset only

## Verb Files in Bootstrap

Bootstrap verb files follow a specific format with a shebang line that defines metadata:

```python
#!moo verb verb_name --on $object_reference
```

The shebang line specifies:

* Verb name(s) - the name(s) by which the verb can be invoked
* `--on` - the object to attach the verb to (uses `$property` syntax to reference system object properties)
* Optional flags like `--dspec` and `--ispec` for direct/indirect object specifiers

After the shebang line, the verb code follows (without a function wrapper - RestrictedPython adds that).

### Example Bootstrap Verb

```python
#!moo verb accept --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Accept an object being moved into this verb's location.
"""

return True
```

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
>>> from moo.sdk import lookup
>>> root = lookup("root")
>>> root.name
'Root Class'
```

For the step-by-step guide to creating your own bootstrap dataset, see {doc}`../how-to/bootstrapping`.
