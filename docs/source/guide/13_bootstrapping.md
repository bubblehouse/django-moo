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
