# Development

Beyond crafting content in-game, there's a lot more development tooling that can be used to
work on the core functions of django-moo.

## Prerequisites

* Docker
* VSCode
  *  with [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) plugin
* Git

## Getting Started

In the django-moo README there are instructions on setting up Docker and using Docker Compose
to run the application stack. You'll still want to follow them all:

> Checkout the project and use Docker Compose to run the necessary components:
>
>     git clone https://gitlab.com/bubblehouse/django-moo
>     cd django-moo
>     docker compose up
>
> Run `migrate`, `collectstatic`, and bootstrap the initial database with some sample objects and users:
>
>     docker compose run webapp manage.py migrate
>     docker compose run webapp manage.py collectstatic
>     docker compose run webapp manage.py moo_init
>     docker compose run webapp manage.py createsuperuser --username phil
>     docker compose run webapp manage.py moo_enableuser --wizard phil Wizard

Once this part is complete, though, you'll want to open up the project folder in VSCode. You should be prompted to
reopen the project as a Dev Container, if not, invoke "Dev Containers: Reopen in Container" from the command bar.

## Environment Setup Details

The project uses **uv** for dependency management and **pytest** for testing.

### Install Dependencies

```bash
uv sync
```

This installs all dependencies including development tools like PyLint, pytest, and coverage analysis.

### Django Management Commands

Essential management commands for development:

```bash
# Migrate database to latest schema
python manage.py migrate

# Create a Django superuser
python manage.py createsuperuser --username yourname

# Connect a Django user to a MOO player/wizard
python manage.py moo_enableuser --wizard yourname YourWizardName

# Initialize the game world with bootstrap data
python manage.py moo_init

# Access Django interactive shell for debugging
python manage.py shell
```

### Environment Variables

Configure these via `docker-compose.override.yml` or `.env`:

- `DJANGO_SETTINGS_MODULE`: Which settings to use (`moo.settings.local` for Docker, `moo.settings.dev` for local)
- `DEBUG`: Enable Django debug mode
- `ALLOWED_HOSTS`: Hosts allowed to connect to the server
- `SECRET_KEY`: Django secret key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Using VSCode with django-moo

The first thing to do with your development environment is to make sure you can run the unit tests:

![django-moo unit tests](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/vscode-testing.png)

In addition to testing core functionality, there's also integration tests for the default verbs at creation time.

### Running the Server

The Dev Containers use the Compose file normally, except for the Celery broker, which isn't run by default. Instead
the terminals you create will all be on the `celery` container instance, and you can run the Celery server in debug
mode using the launch job on the "Run and Debug" tab.

![django-moo debugging](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/vscode-debug.png)

## Testing

### Running Tests

```bash
# Run all tests with coverage reporting
uv run pytest -n auto --cov

# Run a specific test file
uv run pytest -n auto moo/core/tests/test_invoke_verb.py

# Run a specific test function
uv run pytest -n auto moo/core/tests/test_invoke_verb.py::test_successful_verb_execution

# Run with verbose output and stop on first failure
uv run pytest -vv -x

# Run with pdb debugger on failure
uv run pytest --pdb
```

### Test Organization

- **Core tests**: `moo/core/tests/` - Tests for models, permissions, verb execution engine
- **Bootstrap integration tests**: `moo/bootstrap/default_verbs/tests/` - Tests for the default verb implementations
- **Bootstrap verb sources**: `moo/bootstrap/test_verbs/` - MOO verb definitions for the `test` dataset (not pytest tests)
- **Test bootstrap data**: Defined in `moo/bootstrap/test.py`
- **Default game data**: Defined in `moo/bootstrap/default.py`

Shared pytest fixtures live in `moo/conftest.py` and provide a pre-seeded game world for integration tests.

### Writing Tests

All tests should:
- Use `@pytest.mark.django_db` decorator to access the database
- Test both success and failure cases
- Follow PEP 8 naming conventions (test functions start with `test_`)

#### Core unit tests

Core tests exercise models and the verb execution engine without needing a full bootstrap. They typically use `@pytest.mark.django_db` alone:

```python
import pytest
from moo.core import create, lookup
from moo.core.exceptions import PermissionDenied

@pytest.mark.django_db
def test_object_creation_and_properties():
    obj = create("Test Object")
    assert obj.name == "Test Object"

    obj.set_property("description", "A test object")
    assert obj.get_property("description") == "A test object"

@pytest.mark.django_db
def test_permission_denial():
    obj = create("Protected Object")
    obj.owner = lookup("Wizard")
    obj.save()

    with pytest.raises(PermissionDenied):
        obj.can_caller("write")
```

#### Bootstrap integration tests

Tests in `moo/bootstrap/default_verbs/tests/` exercise verbs against a fully bootstrapped world.
They use two shared fixtures from `moo/conftest.py`:

- **`t_init`**: Bootstraps the full game world by running `default.py`. Yields the system object (`#1`). Must be requested with `@pytest.mark.parametrize("t_init", ["default"], indirect=True)`.
- **`t_wizard`**: Returns the Wizard player object, which starts in The Laboratory.

Output sent to the player is captured via a `_writer` callback passed to `code.ContextManager`. Commands are executed with `parse.interpret`. After a verb modifies database state, call `refresh_from_db()` before asserting:

```python
import pytest
from moo.core import code, create, lookup, parse
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_from_inventory(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        widget = create("widget", parents=[system.thing], location=t_wizard)

        parse.interpret(ctx, "drop widget")

        widget.refresh_from_db()
        assert widget.location == lab
        assert not printed
```

Verbs can also be called directly as Python methods inside a `code.ContextManager` block. This is useful for testing helper verbs (message formatters, lock checks, etc.) without going through the command parser:

```python
with code.ContextManager(t_wizard, _writer):
    system = lookup(1)
    widget = create("widget", parents=[system.thing], location=t_wizard)

    # Call the verb directly — equivalent to the MOO expression widget:drop_succeeded_msg()
    assert widget.drop_succeeded_msg() == f"You drop {widget}."

    # Test moveto without the drop command
    lab = t_wizard.location
    widget.moveto(lab)
    widget.refresh_from_db()
    assert widget.location == lab
```

To test that a lock prevents movement, set a `key` property on the destination before calling `moveto`. The lock expression `["!", id]` blocks the object whose id matches:

```python
destination.set_property("key", ["!", widget.id])
widget.moveto(destination)
widget.refresh_from_db()
assert widget.location != destination  # move was blocked
```

For commands that trigger connection-level notifications (movement between rooms, `say`, etc.), wrap the `parse.interpret` call with `pytest.warns`:

```python
with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
    parse.interpret(ctx, "go north")
assert [str(x.message) for x in warnings.list] == [
    f"ConnectionError(#{t_wizard.pk} (Wizard)): You leave ...",
]
```

### Code Quality Tools

```bash
# Run PyLint to check code quality
DJANGO_SETTINGS_MODULE=moo.settings.test uv run pylint moo

# View coverage report
uv run coverage report

# Format code with Black
uv run black moo --line-length 120
```

## Common Development Tasks

### Debugging Objects in Django Shell

```python
python manage.py shell

>>> from moo.core import lookup, create
>>> obj = lookup("root")
>>> obj.name
'Root Class'
>>> obj.properties.all()
<QuerySet [...]>
>>> obj.verbs.all()
<QuerySet [...]>
```

### Testing a Verb

```python
from moo.core import lookup

obj = lookup("some_object")
result = obj.invoke_verb("verb_name", args=["arg1", "arg2"])
print(result)
```

### Adding a New Verb

```python
from moo.core import lookup

obj = lookup("some_object")
obj.add_verb("my_verb", code="""
return "Hello from verb"
""")

result = obj.invoke_verb("my_verb")
```

### Resetting the Database

```bash
# Migrate back to initial state
python manage.py migrate zero

# Re-run migrations
python manage.py migrate

# Bootstrap with default game world
python manage.py moo_init
```

## Performance Profiling

Use pytest-profiling to identify slow operations:

```bash
# Run tests with profiling
uv run pytest --profile

# View the generated profile
python -m pstats .prof
```

## Documentation

Documentation is generated from source code docstrings using Sphinx:

```bash
# Build documentation locally
cd docs
make html

# View the built documentation
open build/html/index.html
```

Always include docstrings on:
- All classes and methods
- All module-level functions
- Complex verb code

## Git Workflow

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make changes and test locally
3. Follow Conventional Commits for commit messages:
   - `feat(core): add new feature`
   - `fix(shell): handle disconnect`
   - `docs(context): update docstring`
4. Push and create a merge request targeting `main`
5. Address review feedback and ensure CI passes

## CI/CD Pipeline

The project uses GitLab CI/CD. On each commit:

1. **Lint stage** - PyLint checks code quality (minimum score 8.0)
2. **Test stage** - pytest runs with coverage tracking
3. **Release stage** (on `main` only) - Semantic versioning and Docker image build
4. **Deploy stage** (on `main` only) - ReadTheDocs documentation build

Check `.gitlab-ci.yml` for the full pipeline configuration.
