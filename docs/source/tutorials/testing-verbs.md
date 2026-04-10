# Writing Tests for Your Verbs

This tutorial shows you how to write automated tests for MOO verbs. By the end you'll know how to capture player output, verify database side effects, call verbs directly without the command parser, and test lock behavior — all using pytest and the fixtures that ship with the project.

## Prerequisites

Before you start:

- Familiarity with {doc}`first-verb` — the tutorial where the `greet` verb is introduced
- A working development environment (see {doc}`../how-to/development`)
- Basic familiarity with pytest

## The verb we're testing

We'll test a `greet` verb on `$thing`. Save this as `moo/bootstrap/default_verbs/thing/greet.py`:

```python
#!moo verb greet --on $thing --dspec none
print(f"You greet {this.name}. It doesn't respond.")
this.location.announce_all_but(context.player, f"{context.player.name} greets {this.name}.")
```

This verb:

- Matches `greet widget` when `widget` is a `$thing` (dspec `none` means no direct object — the verb target is resolved by the command parser matching `widget` to `this`)
- Prints a message to the caller via `print()`
- Announces to everyone else in the room via `announce_all_but()`

## Step 1: Create the test file

Create `moo/bootstrap/default_verbs/tests/test_greet.py`:

```python
import pytest
from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object
```

These are the standard imports for default-verb tests. `code` provides `ContextManager`. `parse` provides `interpret`. `create` and `lookup` are SDK helpers for building test fixtures.

## Step 2: Add the fixtures and markers

Every default-verb test uses two markers and two fixtures:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_greet_prints_to_caller(t_init: Object, t_wizard: Object):
    ...
```

- `@pytest.mark.django_db(transaction=True, reset_sequences=True)` — wraps each test in a real database transaction that is rolled back on exit; `reset_sequences=True` ensures auto-increment IDs reset so tests don't depend on specific object IDs
- `@pytest.mark.parametrize("t_init", ["default"], indirect=True)` — runs the `t_init` fixture with `"default"` as its argument, which bootstraps the full default game world
- `t_init: Object` — the system object (`#1`) after bootstrap; not used directly here but must be listed for the fixture to run
- `t_wizard: Object` — the Wizard player object; used as the actor for all commands

## Step 3: Capture `print()` output

`print()` inside verb code sends output to the player who issued the command. In tests, you capture it by passing a callback to `code.ContextManager`:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_greet_prints_to_caller(t_init: Object, t_wizard: Object):
    printed = []

    with code.ContextManager(t_wizard, printed.append) as ctx:
        system = lookup(1)
        widget = create("widget", parents=[system.thing], location=t_wizard.location)
        parse.interpret(ctx, "greet widget")

    assert printed == ["You greet widget. It doesn't respond."]
```

`code.ContextManager(t_wizard, printed.append)` sets the current player to `t_wizard` for the duration of the `with` block. Every `print()` call inside verb code calls `printed.append`. `parse.interpret(ctx, "greet widget")` dispatches the command through the full verb search pipeline — the same path a real player command takes.

## Step 4: Capture `tell()` and `write()` output

`tell()` and `write()` send output to a specific player object. In production, those players have live SSH connections. In tests, the connection is absent, so `write()` raises a `ConnectionError` which pytest captures as a `RuntimeWarning`.

The `greet` verb calls `announce_all_but()`, which calls `tell()` on every player in the room except the caller. To capture those messages, wrap the `parse.interpret` call in `pytest.warns`:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_greet_announces_to_room(t_init: Object, t_wizard: Object):
    printed = []

    with code.ContextManager(t_wizard, printed.append) as ctx:
        system = lookup(1)
        player = lookup("Player")
        widget = create("widget", parents=[system.thing], location=t_wizard.location)

        with pytest.warns(RuntimeWarning, match="ConnectionError") as w:
            parse.interpret(ctx, "greet widget")

    messages = [str(x.message) for x in w.list]
    assert any("Wizard greets widget." in m for m in messages)
```

`pytest.warns(RuntimeWarning)` catches all `ConnectionError` warnings. Each one has the form `ConnectionError(#N (Name)): <message text>`. Extract message text by converting to string and checking for a substring.

Note that `mock_player_connected` in `conftest.py` patches `is_connected` to return `True` for all objects during tests. This means `tell()` fires normally — without it, no `write()` calls would happen at all.

## Step 5: Test database side effects

When a verb moves an object, modifies a property, or changes ownership, you need to call `refresh_from_db()` before asserting — the in-memory object won't reflect database changes made inside the Celery task:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_moves_object_to_room(t_init: Object, t_wizard: Object):
    printed = []

    with code.ContextManager(t_wizard, printed.append) as ctx:
        system = lookup(1)
        lab = t_wizard.location
        widget = create("widget", parents=[system.thing], location=t_wizard)

        with pytest.warns(RuntimeWarning, match="ConnectionError"):
            parse.interpret(ctx, "drop widget")

        widget.refresh_from_db()
        assert widget.location == lab

    assert printed == ["You drop widget."]
```

Without `refresh_from_db()`, `widget.location` still shows the pre-command value.

## Step 6: Call verbs directly (skip the parser)

For helper verbs — message formatters, lock checks, anything called as a method rather than a player command — call them directly on the object inside a `code.ContextManager` block:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_message_verbs(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        widget = create("widget", parents=[system.thing], location=t_wizard)

        assert widget.take_succeeded_msg() == f"You take {widget.title()}."
        assert widget.drop_succeeded_msg() == f"You drop {widget.title()}."
        assert widget.odrop_succeeded_msg() == f"{t_wizard.name} drops {widget.title()}."
```

This is equivalent to the MOO expression `widget:take_succeeded_msg()`. It runs the verb in the context of `t_wizard` as the current player.

## Step 7: Test a lock guard

The `moveto()` method checks the destination's `key` property before moving an object. Set a key expression to block movement and verify the object stays put:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto_blocked_by_lock(t_init: Object, t_wizard: Object):
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        rooms = lookup("Generic Room")
        lab = t_wizard.location
        destination = create("Locked Room", parents=[rooms], location=None)
        widget = create("widget", parents=[system.thing], location=lab)

        # Block the widget by ID: lock expression ["!", id] means "not this object"
        destination.set_property("key", ["!", widget.id])

        widget.moveto(destination)
        widget.refresh_from_db()

        assert widget.location == lab  # move was blocked
```

## Step 8: Using the `setup_item` fixture

The `setup_item` fixture from `moo/bootstrap/default_verbs/tests/conftest.py` creates a `$thing` in any location, reducing boilerplate:

```python
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_give_to_player(t_init: Object, t_wizard: Object, setup_item):
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        player_obj = lookup("Player")
        widget = setup_item(t_wizard, "widget")  # creates $thing in t_wizard's inventory

        parse.interpret(ctx, "give widget to Player")
        widget.refresh_from_db()

    assert widget.location == player_obj
```

`setup_item(location, name)` creates a `$thing` child at the given location. The `name` argument defaults to `"red ball"`.

## What just happened

`code.ContextManager` establishes the `context` proxy for a given player. Every piece of verb code that reads `context.player`, `context.caller`, or `context.parser` is reading state set by this context manager. `parse.interpret` dispatches a command string through the same verb search pipeline that live player commands use — object resolution, preposition matching, dspec checking — so tests cover the full dispatch path.

`tell()` and `write()` raise `ConnectionError` for players without a live session because there is no SSH connection to send output to. The `mock_player_connected` autouse fixture (in `moo/conftest.py`) patches `is_connected()` to return `True` so these calls proceed normally in test. The `ConnectionError` that arrives is therefore a synthetic stand-in for the actual message delivery.

## Where to go next

- {doc}`../how-to/development` — The full test toolchain: running tests with coverage, pylint, and the VSCode test runner
- {doc}`../reference/runtime` — The complete `context` variable reference
- {doc}`../how-to/creating-verbs` — The full verb code format including shebang syntax, output mechanisms, and error handling
