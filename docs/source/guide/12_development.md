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

The project uses **Poetry** for dependency management and **pytest** for testing.

### Install Dependencies

```bash
poetry install
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
poetry run pytest -n auto --cov

# Run a specific test file
poetry run pytest -n auto moo/core/tests/test_invoke_verb.py

# Run a specific test function
poetry run pytest -n auto moo/core/tests/test_invoke_verb.py::test_successful_verb_execution

# Run with verbose output and stop on first failure
poetry run pytest -vv -x

# Run with pdb debugger on failure
poetry run pytest --pdb
```

### Test Organization

- **Core tests**: `moo/core/tests/` - Uses the `test` bootstrap dataset
- **Bootstrap tests**: `moo/core/bootstrap/test_verbs/` - Tests for the default verb implementations
- **Test data**: Defined in `moo/core/bootstrap/test.py`
- **Default game data**: Defined in `moo/core/bootstrap/default.py`

### Writing Tests

All tests should:
- Use `@pytest.mark.django_db` decorator to access the database
- Test both success and failure cases
- Include descriptive assertion messages
- Follow PEP 8 naming conventions (test functions start with `test_`)

```python
import pytest
from moo.core import create, lookup
from moo.core.exceptions import PermissionDenied

@pytest.mark.django_db
def test_object_creation_and_properties():
    """Verify that objects can be created with properties."""
    obj = create("Test Object")
    assert obj.name == "Test Object"

    obj.set_property("description", "A test object")
    assert obj.get_property("description") == "A test object"

@pytest.mark.django_db
def test_permission_denial():
    """Verify that permission checks work correctly."""
    obj = create("Protected Object")
    obj.owner = lookup("Wizard")
    obj.save()

    # Should raise PermissionDenied when caller lacks write permission
    with pytest.raises(PermissionDenied):
        obj.can_caller("write")
```

### Code Quality Tools

```bash
# Run PyLint to check code quality
DJANGO_SETTINGS_MODULE=moo.settings.test poetry run pylint moo

# View coverage report
poetry run coverage report

# Format code with Black
poetry run black moo --line-length 120
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
poetry run pytest --profile

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
   - `docs(api): update docstring`
4. Push and create a merge request targeting `main`
5. Address review feedback and ensure CI passes

## CI/CD Pipeline

The project uses GitLab CI/CD. On each commit:

1. **Lint stage** - PyLint checks code quality (minimum score 8.0)
2. **Test stage** - pytest runs with coverage tracking
3. **Release stage** (on `main` only) - Semantic versioning and Docker image build
4. **Deploy stage** (on `main` only) - ReadTheDocs documentation build

Check `.gitlab-ci.yml` for the full pipeline configuration.
