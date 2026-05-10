# Bootstrapping Reference

A bootstrap is a Python package that populates an empty database with
the objects, properties, and verbs that make up a DjangoMOO world.
Without one, a fresh database has no System Object, no Wizard, and
nothing to log into.

For a step-by-step walkthrough of writing your own dataset, see
{doc}`../tutorials/custom-world`. For task recipes (sync after edits,
verb replacement, idempotent updates, debugging), see
{doc}`../how-to/bootstrapping`.

## Available datasets

`default` — the production game world. Loaded with:

```bash
docker compose run webapp manage.py moo_init --bootstrap default
```

Lives at `moo/bootstrap/default/`. The package contains an orchestrator
`bootstrap.py` plus numbered sub-scripts (`000_initialize.py`,
`010_core_classes.py`, ..., `999_finalize.py`) executed in sorted order.
The package's `__init__.py` is intentionally empty so importing the
package (e.g. for test discovery) does not run database setup; the
orchestrator is invoked explicitly by `moo_init` via `bootstrap.py`.
Verb sources live in the sibling `moo/bootstrap/default/verbs/` package,
organised by root-class name; tests live in `moo/bootstrap/default/tests/`.

`zork1` — an example bootstrap derived from the original Infocom
*Zork I: The Great Underground Empire* source (released by
Microsoft / Activision under the MIT License in 2025). It is provided
as a reference implementation, not a recommended starting point for a
new world. Loaded with:

```bash
docker compose run webapp manage.py moo_init --bootstrap zork1
```

Lives at `moo/bootstrap/zork1/`. The package contains the orchestrator
`bootstrap.py`, numbered `010_classes.py` … `040_exits.py` setup
scripts, ~200 verb files implementing the original ZIL routines, a
`$zork_sdk` runtime under `verbs/zork_sdk/`, and player-facing
commands under `verbs/commands/`. The translator that produced this
dataset lives in the moo-agent project; see its `reference/zil-importer`
for how the dataset relates to the upstream Zork I source.

`test` — a minimal dataset used by the pytest `t_init` fixture in
`moo/conftest.py`. It is *not* loadable via `moo_init`. It exists as a
flat module (`moo/bootstrap/test.py`) and creates only what the unit
tests need to exercise the verb execution engine.

## What initialization gives you

`bootstrap.initialize_dataset(name)` is the entry point every bootstrap
package calls first. It is idempotent and produces:

- A `Repository` row (`slug=name`, `prefix=moo/bootstrap/<name>/verbs`)
  used by `load_verbs` to locate verb sources.
- The full set of `Permission` rows defined by
  `settings.DEFAULT_PERMISSIONS`.
- The lexer's preposition table (`Pattern.initializePrepositions`).
- The **System Object** (`pk=1`, `name="System Object"`).
- Three LambdaMOO-style sentinel objects with the lowest possible PKs:
  `nothing` (#2), `ambiguous_match` (#3), `failed_match` (#4).
- A **Wizard** Object with a stub `accept` verb returning `True`.
- A Django `User` named `wizard` and a `Player` row linking the user to
  the Wizard Object with `wizard=True`.
- Wizard ownership of the System Object, the sentinels, and itself.

What it does *not* do — and what your bootstrap package is responsible
for — is create root classes (Room, Thing, Player, etc.), starting
rooms, exits, or any verbs beyond Wizard's stub `accept`. The default
permission application that runs on every new object is handled
natively by `moo.core.utils.apply_default_permissions`; no
`set_default_permissions` verb on the System Object is required.

## Orchestrator pattern

Every loadable bootstrap is a Python package whose `bootstrap.py` entry
point:

1. Calls `bootstrap.initialize_dataset(name)`.
2. Builds a `_namespace` dict containing every name the sub-scripts
   need (`bootstrap`, `lookup`, `wizard`, `sys`, etc.).
3. Discovers numbered `.py` files in the package via
   `importlib.resources.files("moo.bootstrap.<name>").iterdir()`.
4. Runs each script via `exec(compile(...), _namespace)` inside a
   `code.ContextManager(wizard, log.info, site=wizard.site)` block so
   ownership, permissions, and the active site track to the Wizard player.
5. Either calls `bootstrap.load_verbs` directly at the end, or defers
   that to a `999_finalize.py` script.

The package's `__init__.py` is left empty; `moo_init` invokes
`bootstrap.py` explicitly via `load_python` rather than importing the
package, so test collection can import the package safely.

`moo/bootstrap/default/bootstrap.py` is the canonical example.

## Function reference

```{eval-rst}
.. py:currentmodule:: moo.bootstrap
.. autofunction:: initialize_dataset
   :no-index:
.. autofunction:: get_or_create_object
   :no-index:
.. autofunction:: load_verbs
   :no-index:
.. autofunction:: load_verb_source
   :no-index:
.. autofunction:: parse_shebang
   :no-index:
```

`get_or_create_object` returns a `(object, created)` tuple. It only
attaches `parents` on first creation to avoid duplicate-relationship
errors. Calling it on an existing database is a no-op for the object
itself, which makes top-level use safe under `moo_init --sync`.

`load_verb_source` parses a `#!moo verb` shebang from a single file and
calls `obj.add_verb()`. Pass `replace=True` to overwrite the verb source
in place; the default skips files whose verbs already exist.

`load_verbs` walks a Python package recursively, calling
`load_verb_source` for every `.py` file with a shebang. The directory
structure inside the package is purely organisational — only the
`--on` line in each shebang determines where the verb attaches.

`parse_shebang` is the same parser used by both `load_verb_source` and
`@edit verb`. It returns `(names, on, dspec, ispec)` or `None` if the
first line is not a `#!moo verb` shebang. Useful when you need to
extract verb metadata from user-supplied source.

## Verb files in bootstrap

Every verb file begins with a shebang:

```python
#!moo verb accept --on $room
```

The shebang is parsed by `parse_shebang` and supplies `--on` (the
target object), the verb name(s), and optional `--dspec`/`--ispec`
flags. After the shebang, the verb body follows without a function
wrapper — RestrictedPython adds one at compile time.

For the full shebang grammar and verb authoring patterns, see
{doc}`../how-to/creating-verbs`.

## Running bootstrap in development

Initialize a fresh database:

```bash
docker compose run webapp manage.py migrate
docker compose run webapp manage.py moo_init --bootstrap default
```

Sync an existing database to pick up new verbs and objects without
resetting it. This is the right tool for almost every iteration cycle:

```bash
docker compose run webapp manage.py moo_init --bootstrap default --sync
```

If you need a true reset (destroys all data), tear down and recreate
the postgres container rather than running `migrate zero`:

```bash
docker compose down -v
docker compose up -d
docker compose run webapp manage.py migrate
docker compose run webapp manage.py moo_init --bootstrap default
```

`-v` drops the postgres volume so the next `up` starts from an empty
database.

Inspect the bootstrapped state from the Django shell:

```bash
docker compose run webapp manage.py shell
```

```python
>>> from moo.sdk import lookup
>>> sys = lookup(1)
>>> sys.name
'System Object'
>>> sys.root_class.name
'Root Class'
>>> lookup("Wizard").is_wizard()
True
```

`lookup()` accepts an object PK, an exact `name`, or any of an
object's aliases. It raises `NoSuchObjectError` if nothing matches.
