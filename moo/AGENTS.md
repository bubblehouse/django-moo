# AGENTS.md: moo Package Guide

This document provides specific guidance for the `moo` package, the main DjangoMOO application.

## Package Structure

The `moo` package is organized as a Django project with the following main components:

### `/moo/core` - Core Game Engine

**Purpose**: Contains all core MOO game logic, models, and utilities.

**Key Components**:
- `models/`: Django ORM models for game objects
  - `object.py`: The `Object` model - core entity in the MOO world
  - `verb.py`: The `Verb` model - functions/methods that objects can execute
  - `property.py`: The `Property` model - key-value attributes on objects
  - `acl.py`: Access Control List models and permission system
  - `auth.py`: Authentication and player-related models
- `code.py`: RestrictedPython code compilation and execution
- `parse.py`: MOO language parser and lexer
- `management/commands/`: Django CLI commands for administration
- `tests/`: Comprehensive test suite for core functionality
- `admin.py`: Django admin interface configuration
- `tasks.py`: Celery task definitions for async operations

**Important Patterns**:
- Objects use Django's ORM model inheritance
- Properties support inheritance; child objects inherit parent properties
- Verbs are Python code compiled and sandboxed via RestrictedPython
- All model access should use Django QuerySets, never raw SQL

### `/moo/bootstrap` - Database Initialization

**Purpose**: Contains bootstrap datasets and verb files that initialize the game database.

**Key Components**:
- `default.py`: Creates the production game world with rooms, players, and other game objects
- `test.py`: Creates a minimal test dataset used by pytest
- `default_verbs/`: Directory containing verb files for the default dataset
- `test_verbs/`: Directory containing verb files for the test dataset

### `/moo/shell` - SSH Server & Terminal Interface

**Purpose**: Provides SSH server implementation and interactive terminal for players.

**Key Components**:
- `server.py`: AsyncSSH server implementation
- `prompt.py`: Interactive REPL and command processing
- `management/commands/`: Commands for shell startup

**Important Patterns**:
- Uses asyncio for concurrent connections
- Integrates with Django's user authentication
- Supports both password and SSH key authentication

### `/moo/settings` - Configuration

**Purpose**: Django settings modules for different environments.

**Files**:
- `base.py`: Core settings shared across all environments
- `dev.py`: Development environment overrides
- `local.py`: Local/Docker environment overrides
- `test.py`: Test environment configuration for pytest

**Important Settings to Know**:
- `ALLOWED_MODULES`: Python modules accessible to verb code
- `ALLOWED_BUILTINS`: Builtin functions accessible to verbs
- `DEFAULT_PERMISSIONS`: Core permission strings for the ACL system
- `PREPOSITIONS`: MOO preposition definitions

## Development Guidelines for `moo` Package

### Adding New Models

1. Create the model in `moo/core/models/<component>.py`
2. Import it in `moo/core/models/__init__.py`
3. Register it in `moo/core/admin.py` if it needs admin access
4. Create a migration: `python manage.py makemigrations`
5. Create corresponding tests in `moo/core/tests/`

### Adding New Management Commands

1. Create file: `moo/core/management/commands/<command_name>.py`
2. Inherit from `django.core.management.base.Command`
3. Implement `add_arguments()` and `handle()` methods
4. Document the command in project documentation

### Writing Verb Code

Verbs are stored as `Verb` model instances with code compiled by RestrictedPython. When executed, verb code is wrapped in a function signature before being called with the required parameters.

```python
#!moo verb emote --on $room

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

if context.parser.words:
    message = " ".join(context.parser.words[1:])
else:
    message = " ".join(args)

context.caller.tell("You " + message)
this.emote1(message)
```

When executing a verb:
- The execution context includes special variables: `this`, `passthrough`, `_`, `args`, `kwargs`, and `verb_name`
  - `this` – the object where the verb was found
  - `passthrough()` - when used by a child object, passes control to the verb of the same name defined on a parent object
  - `_` - a reference to the System Object
  - `args` - if the verb is invoked as a function, this contains any positional arguments
  - `kwargs` - if the verb is invoked as a function, this contains any named arguments
  - `verb_name` - a verb can have multiple names; this is the particular name used to invoke this verb.
- Many verbs include `from moo.core import context`; the `context` object has a number of helpful properties:
  - `caller` - When a verb begins to execute, `caller` is set to the owner of the verb; calls to `set_task_perms` can change this.
  - `player` - This is always a reference to the current player who should receive all output from the running verb.
  - `writer()` - This callable is used to write directly to an object's player terminal, if connected.
  - `parser` - If a verb was invoked by the command parser, the `moo.core.parse.Parser` instance can be retreived here.
  - `task_id` - The current executing Celery task ID, for informational purposes
- The verb has access only to whitelisted modules and builtins (see settings)
- Errors in verb execution are caught and reported to the player

### Working with Permissions

The permission system uses permission strings:
- `"read"`: Can read properties
- `"write"`: Can modify properties
- `"execute"`: Can execute verbs
- `"move"`: Can move objects
- `"transmute"`: Can change object's class
- `"derive"`: Can inherit from object
- etc.

Always check permissions before allowing operations:

```python
obj = args[0]
if not obj.can_caller("write"):
    print("You don't have write permission")
```

### Database Query Best Practices

Use Django's ORM features to avoid N+1 queries:

```python
# GOOD: Use select_related for foreign keys
objects = Object.objects.select_related('owner', 'location')

# GOOD: Use prefetch_related for many-to-many and reverse relations
objects = Object.objects.prefetch_related('properties', 'children')

# AVOID: This causes N+1 queries
for obj in Object.objects.all():
    print(obj.owner.name)  # Query for each object
```

### Testing Guidelines

There are two distinct test types in this package:

#### Core unit tests (`moo/core/tests/`)

These test models and the verb execution engine directly, without a full bootstrap. Use `@pytest.mark.django_db` alone:

```python
import pytest
from moo.core import create, lookup
from moo.core.exceptions import PermissionDenied

@pytest.mark.django_db
def test_object_creation():
    obj = create("Test Object")
    assert obj.name == "Test Object"

@pytest.mark.django_db
def test_permission_check():
    obj = create("Protected Object")
    obj.owner = lookup("Wizard")
    obj.save()
    with pytest.raises(PermissionDenied):
        obj.can_caller("write")
```

#### Bootstrap integration tests (`moo/bootstrap/default_verbs/tests/`)

These exercise verbs against a fully bootstrapped `default` world. They require two shared fixtures from `moo/conftest.py`:

- **`t_init`**: Bootstraps `default.py`. Must be requested via `@pytest.mark.parametrize("t_init", ["default"], indirect=True)`.
- **`t_wizard`**: Returns the Wizard player, who starts in The Laboratory.

Capture player output with a `_writer` callback. Run commands through `parse.interpret`. Call `refresh_from_db()` before asserting database-backed state:

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

Verbs can also be called as Python methods inside `code.ContextManager`, bypassing the parser — useful for testing helpers and message verbs:

```python
with code.ContextManager(t_wizard, _writer):
    system = lookup(1)
    widget = create("widget", parents=[system.thing], location=t_wizard)
    assert widget.drop_succeeded_msg() == f"You drop {widget}."
```

For commands that send connection-level notifications (movement, `say`), wrap with `pytest.warns`:

```python
with pytest.warns(RuntimeWarning, match=r"ConnectionError") as warnings:
    parse.interpret(ctx, "go north")
assert "You leave" in str(warnings.list[0].message)
```

## Common Tasks

### Debugging in Development

1. **Django Shell**: `python manage.py shell` - Interactive Python shell with Django
2. **Database Inspection**: Use Django shell to query models
3. **Celery Debugging**: Check Redis and worker logs
4. **SSH Debugging**: Check server logs for connection issues

### Running Specific Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest moo/core/tests/test_invoke_verb.py

# Run specific test function
uv run pytest moo/core/tests/test_invoke_verb.py::test_successful_verb_execution

# Run with verbose output
uv run pytest -vv

# Run with pdb on failure
uv run pytest --pdb
```

## Performance Considerations

1. **Caching**: Use Redis for frequently accessed objects or computed properties
2. **Lazy Loading**: Use `.defer()` and `.only()` to load only needed fields
3. **Aggregation**: Use Django's aggregation functions instead of Python loops
4. **Indexing**: Add `db_index=True` to frequently filtered fields
5. **Celery Tasks**: All code and command-parser invocations are executed as tasks inside Celery workers. Creating new Celery Tasks is uncommon.

## Important Notes

- **Never bypass RestrictedPython**: It's a security boundary for user code
- **Always validate player input**: Assume all input is potentially hostile
- **Use transactions carefully**: Database consistency is critical for a game server
- **Document API changes**: Update docstrings when changing public interfaces
